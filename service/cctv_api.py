"""Production CCTV ALPR API service."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
from fastapi import FastAPI

from fast_alpr import ALPR


class CctvProcessor:
    """Continuously read a CCTV source and keep latest ALPR report in memory + disk."""

    def __init__(self) -> None:
        # Backward-compatible fallback for legacy typo used in some deployment scripts.
        self.source = os.getenv("CCTV_SOURCE") or os.getenv("CTV_SOURCE") or "assets/test_image.png"
        self.frame_stride = max(1, int(os.getenv("FRAME_STRIDE", "5")))
        self.reconnect_wait_seconds = float(os.getenv("RECONNECT_WAIT_SECONDS", "2"))
        self.artifact_dir = Path(os.getenv("ARTIFACT_DIR", "artifacts"))
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.report_path = self.artifact_dir / "latest_report.json"
        self.snapshot_path = self.artifact_dir / "latest_frame.jpg"
        self.events_path = self.artifact_dir / "events.jsonl"

        self._lock = threading.Lock()
        self._latest_report: dict[str, Any] = {
            "status": "initializing",
            "source": self.source,
            "updated_at": None,
            "detections": [],
        }
        self._stop_event = threading.Event()

        self.alpr = ALPR(
            detector_model=os.getenv("DETECTOR_MODEL", "yolo-v9-t-384-license-plate-end2end"),
            ocr_model=os.getenv("OCR_MODEL", "cct-xs-v1-global-model"),
        )

    def start(self) -> None:
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def latest(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._latest_report)

    def _run(self) -> None:
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

                results = self.alpr.predict(frame)
                annotated = self.alpr.draw_predictions(frame.copy())
                detections: list[dict[str, Any]] = []
                for item in results:
                    row = {
                        "detection": {
                            "label": item.detection.label,
                            "confidence": item.detection.confidence,
                            "bounding_box": asdict(item.detection.bounding_box),
                        },
                        "ocr": asdict(item.ocr) if item.ocr is not None else None,
                    }
                    detections.append(row)

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

                self.report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                cv2.imwrite(str(self.snapshot_path), annotated)
                with self.events_path.open("a", encoding="utf-8") as events_file:
                    events_file.write(json.dumps(payload, ensure_ascii=False) + "\n")

            capture.release()
            time.sleep(self.reconnect_wait_seconds)

    def _set_error(self, message: str) -> None:
        payload = {
            "status": "error",
            "source": self.source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "detections": [],
        }
        with self._lock:
            self._latest_report = payload
        self.report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


processor = CctvProcessor()
app = FastAPI(title="FastALPR CCTV Service", version="1.0.0")


@app.on_event("startup")
def startup_event() -> None:
    processor.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    processor.stop()


@app.get("/health")
def health() -> dict[str, str]:
    latest = processor.latest()
    return {"status": latest.get("status", "unknown")}


@app.get("/latest")
def latest() -> dict[str, Any]:
    return processor.latest()
