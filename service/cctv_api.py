"""Production CCTV ALPR API service with Thai plate support and database integration."""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import ProcessingStatus, VehicleLog, create_tables, get_engine, get_session_maker
from fast_alpr import ALPR
from utils.thai_plate_parser import parse_thai_plate


class VerifyRequest(BaseModel):
    """Request model for manual verification endpoint."""

    log_id: int
    plate_category: str
    plate_number: str
    province: str


def _resolve_onnx_providers() -> list[str]:
    """Resolve ONNX Runtime execution providers from env + availability."""
    configured = os.getenv("ONNX_PROVIDERS")
    if configured:
        return [provider.strip() for provider in configured.split(",") if provider.strip()]

    available = set(ort.get_available_providers())
    preferred = ["CUDAExecutionProvider", "CPUExecutionProvider"]

    if os.getenv("ENABLE_TENSORRT", "0") == "1":
        preferred.insert(0, "TensorrtExecutionProvider")

    providers = [provider for provider in preferred if provider in available]
    return providers or ["CPUExecutionProvider"]


class CctvProcessor:
    """
    Continuously read a CCTV source and keep latest ALPR report in memory + disk + database.
    
    Enhanced with Thai license plate support and PostgreSQL integration.
    """

    def __init__(self) -> None:
        # Source configuration
        self.source = os.getenv("CCTV_SOURCE") or os.getenv("CTV_SOURCE") or "assets/test_image.png"
        self.frame_stride = max(1, int(os.getenv("FRAME_STRIDE", "5")))
        self.reconnect_wait_seconds = float(os.getenv("RECONNECT_WAIT_SECONDS", "2"))
        
        # Directory configuration
        self.artifact_dir = Path(os.getenv("ARTIFACT_DIR", "artifacts"))
        self.dataset_dir = Path(os.getenv("DATASET_DIR", "dataset"))
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for images
        self.images_dir = self.artifact_dir / "images"
        self.crops_dir = self.artifact_dir / "crops"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.crops_dir.mkdir(parents=True, exist_ok=True)
        
        # Training dataset directory (for MLPR verified crops)
        self.training_dir = self.dataset_dir / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        
        # Legacy file paths (for backward compatibility)
        self.report_path = self.artifact_dir / "latest_report.json"
        self.snapshot_path = self.artifact_dir / "latest_frame.jpg"
        self.events_path = self.artifact_dir / "events.jsonl"

        # Database setup
        database_url = os.getenv("DATABASE_URL", "postgresql://alpr_user:alpr_password@localhost:5432/thai_alpr")
        self.engine = get_engine(database_url)
        create_tables(self.engine)
        self.SessionMaker = get_session_maker(self.engine)

        # Confidence threshold for automatic acceptance
        self.high_confidence_threshold = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.95"))

        self._lock = threading.Lock()
        self._latest_report: dict[str, Any] = {
            "status": "initializing",
            "source": self.source,
            "updated_at": None,
            "detections": [],
        }
        self._stop_event = threading.Event()
        
        # Initialize ALPR with Thai support
        providers = _resolve_onnx_providers()
        self.alpr = ALPR(
            detector_model=os.getenv("DETECTOR_MODEL", "yolo-v9-t-384-license-plate-end2end"),
            ocr_model=os.getenv("OCR_MODEL", "cct-xs-v1-global-model"),
            detector_providers=providers,
            ocr_providers=providers,
            parse_thai=True,
        )

    def start(self) -> None:
        """Start the CCTV processing thread."""
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def stop(self) -> None:
        """Stop the CCTV processing thread."""
        self._stop_event.set()

    def latest(self) -> dict[str, Any]:
        """Get the latest processing report."""
        with self._lock:
            return dict(self._latest_report)

    def verify_and_train(self, log_id: int, plate_category: str, plate_number: str, province: str) -> VehicleLog:
        """
        Verify a vehicle log manually and copy crop to training dataset.
        
        Args:
            log_id: Database log ID
            plate_category: Corrected plate category
            plate_number: Corrected plate number
            province: Corrected province
            
        Returns:
            Updated VehicleLog
        """
        db: Session = self.SessionMaker()
        try:
            log = db.query(VehicleLog).filter(VehicleLog.id == log_id).first()
            if not log:
                raise ValueError(f"Log ID {log_id} not found")
            
            # Update the log with corrected information
            log.plate_category = plate_category
            log.plate_number = plate_number
            log.province = province
            log.status = ProcessingStatus.MLPR.value
            
            db.commit()
            db.refresh(log)
            
            # Copy crop image to training dataset
            if log.crop_path and os.path.exists(log.crop_path):
                # Create a meaningful filename for training data
                timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                plate_text = f"{plate_category}_{plate_number}_{province}".replace(" ", "_")
                training_filename = f"{timestamp_str}_{plate_text}_{log_id}.jpg"
                training_path = self.training_dir / training_filename
                
                shutil.copy2(log.crop_path, training_path)
                print(f"Copied verified crop to training dataset: {training_path}")
            
            return log
            
        except Exception as exc:
            db.rollback()
            raise exc
        finally:
            db.close()

    def _save_to_database(
        self,
        image_path: str,
        crop_path: str,
        detection_data: dict,
        ocr_data: dict | None,
        thai_data: dict,
    ) -> VehicleLog:
        """Save detection result to database."""
        db: Session = self.SessionMaker()
        try:
            # Determine confidence and status
            ocr_confidence = ocr_data.get("confidence", 0.0) if ocr_data else 0.0
            detection_confidence = detection_data.get("confidence", 0.0)
            
            # Set status based on confidence threshold
            if ocr_confidence >= self.high_confidence_threshold:
                status = ProcessingStatus.ALPR.value
            else:
                status = ProcessingStatus.PENDING.value
            
            # Create vehicle log
            vehicle_log = VehicleLog(
                timestamp=datetime.now(timezone.utc),
                image_path=image_path,
                crop_path=crop_path,
                plate_category=thai_data.get("category"),
                plate_number=thai_data.get("number"),
                province=thai_data.get("province"),
                confidence=ocr_confidence,
                status=status,
                raw_text=ocr_data.get("text") if ocr_data else None,
                detection_confidence=detection_confidence,
                bounding_box=json.dumps(detection_data.get("bounding_box")),
            )
            
            db.add(vehicle_log)
            db.commit()
            db.refresh(vehicle_log)
            
            return vehicle_log
            
        except Exception as exc:
            db.rollback()
            print(f"Database error: {exc}")
            raise exc
        finally:
            db.close()

    def _run(self) -> None:
        """Main processing loop."""
        while not self._stop_event.is_set():
            capture = cv2.VideoCapture(self.source)
            if not capture.isOpened():
                self._set_error(f"Cannot open CCTV source: {self.source}")
                time.sleep(self.reconnect_wait_seconds)
                continue

            frame_index = 0
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    self._set_error("CCTV stream ended/unavailable, reconnecting...")
                    break

                frame_index += 1
                if frame_index % self.frame_stride != 0:
                    continue

                # Run ALPR detection
                results = self.alpr.predict(frame)
                annotated = self.alpr.draw_predictions(frame.copy())
                
                # Save full frame
                timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                full_image_path = self.images_dir / f"frame_{timestamp_str}.jpg"
                cv2.imwrite(str(full_image_path), frame)
                
                detections: list[dict[str, Any]] = []
                
                for idx, item in enumerate(results):
                    # Save cropped plate
                    bbox = item.detection.bounding_box
                    x1, y1 = max(bbox.x1, 0), max(bbox.y1, 0)
                    x2, y2 = min(bbox.x2, frame.shape[1]), min(bbox.y2, frame.shape[0])
                    cropped_plate = frame[y1:y2, x1:x2]
                    
                    crop_path = self.crops_dir / f"crop_{timestamp_str}_{idx}.jpg"
                    cv2.imwrite(str(crop_path), cropped_plate)
                    
                    # Prepare data for database
                    detection_data = {
                        "label": item.detection.label,
                        "confidence": item.detection.confidence,
                        "bounding_box": asdict(item.detection.bounding_box),
                    }
                    
                    ocr_data = asdict(item.ocr) if item.ocr is not None else None
                    
                    thai_data = {
                        "category": item.plate_category,
                        "number": item.plate_number,
                        "province": item.province,
                    }
                    
                    # Save to database
                    try:
                        vehicle_log = self._save_to_database(
                            image_path=str(full_image_path),
                            crop_path=str(crop_path),
                            detection_data=detection_data,
                            ocr_data=ocr_data,
                            thai_data=thai_data,
                        )
                        
                        # Prepare detection data for JSON report
                        row = {
                            "db_id": vehicle_log.id,
                            "detection": detection_data,
                            "ocr": ocr_data,
                            "thai_plate": thai_data,
                            "status": vehicle_log.status,
                        }
                        detections.append(row)
                        
                    except Exception as e:
                        print(f"Error saving to database: {e}")
                        # Still add to detections for legacy JSON report
                        row = {
                            "db_id": None,
                            "detection": detection_data,
                            "ocr": ocr_data,
                            "thai_plate": thai_data,
                            "status": "ERROR",
                        }
                        detections.append(row)

                # Update in-memory report
                payload = {
                    "status": "running",
                    "source": self.source,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "frame_index": frame_index,
                    "plates_detected": len(results),
                    "detections": detections,
                }
                
                with self._lock:
                    self._latest_report = payload

                # Save legacy files
                self.report_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                cv2.imwrite(str(self.snapshot_path), annotated)
                with self.events_path.open("a", encoding="utf-8") as events_file:
                    events_file.write(json.dumps(payload, ensure_ascii=False) + "\n")

            capture.release()
            time.sleep(self.reconnect_wait_seconds)

    def _set_error(self, message: str) -> None:
        """Set error status in report."""
        payload = {
            "status": "error",
            "source": self.source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "detections": [],
        }
        with self._lock:
            self._latest_report = payload
        self.report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# Initialize processor and FastAPI app
processor = CctvProcessor()
app = FastAPI(title="FastALPR Thai CCTV Service", version="2.0.0")


@app.on_event("startup")
def startup_event() -> None:
    """Start CCTV processor on startup."""
    processor.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    """Stop CCTV processor on shutdown."""
    processor.stop()


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    latest = processor.latest()
    return {"status": latest.get("status", "unknown")}


@app.get("/latest")
def latest() -> dict[str, Any]:
    """Get latest ALPR report."""
    return processor.latest()


@app.get("/logs")
def get_logs(skip: int = 0, limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
    """
    Get vehicle logs from database.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status (PENDING, ALPR, MLPR)
    """
    db: Session = processor.SessionMaker()
    try:
        query = db.query(VehicleLog)
        
        if status:
            query = query.filter(VehicleLog.status == status)
        
        logs = query.order_by(VehicleLog.timestamp.desc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "image_path": log.image_path,
                "crop_path": log.crop_path,
                "plate_category": log.plate_category,
                "plate_number": log.plate_number,
                "province": log.province,
                "confidence": log.confidence,
                "status": log.status,
                "raw_text": log.raw_text,
            }
            for log in logs
        ]
    finally:
        db.close()


@app.post("/verify")
def verify_log(request: VerifyRequest) -> dict[str, Any]:
    """
    Manually verify and correct a vehicle log.
    
    Changes status to MLPR and copies crop to training dataset.
    """
    try:
        updated_log = processor.verify_and_train(
            log_id=request.log_id,
            plate_category=request.plate_category,
            plate_number=request.plate_number,
            province=request.province,
        )
        
        return {
            "success": True,
            "log_id": updated_log.id,
            "status": updated_log.status,
            "plate_category": updated_log.plate_category,
            "plate_number": updated_log.plate_number,
            "province": updated_log.province,
            "message": "Log verified and crop added to training dataset",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}") from e


@app.get("/stats")
def get_stats() -> dict[str, Any]:
    """Get system statistics."""
    db: Session = processor.SessionMaker()
    try:
        total_logs = db.query(VehicleLog).count()
        pending_logs = db.query(VehicleLog).filter(VehicleLog.status == ProcessingStatus.PENDING.value).count()
        alpr_logs = db.query(VehicleLog).filter(VehicleLog.status == ProcessingStatus.ALPR.value).count()
        mlpr_logs = db.query(VehicleLog).filter(VehicleLog.status == ProcessingStatus.MLPR.value).count()
        
        # Calculate accuracy (ALPR + MLPR vs total)
        verified_logs = alpr_logs + mlpr_logs
        accuracy = (verified_logs / total_logs * 100) if total_logs > 0 else 0.0
        
        return {
            "total_logs": total_logs,
            "pending_review": pending_logs,
            "auto_detected": alpr_logs,
            "manually_verified": mlpr_logs,
            "accuracy_percentage": round(accuracy, 2),
        }
    finally:
        db.close()