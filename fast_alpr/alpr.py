"""
ALPR module with Thai license plate support.
"""

import os
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
import onnxruntime as ort
from fast_plate_ocr.inference.hub import OcrModel
from open_image_models.detection.core.hub import PlateDetectorModel

from fast_alpr.base import BaseDetector, BaseOCR, DetectionResult, OcrResult
from fast_alpr.default_detector import DefaultDetector
from fast_alpr.default_ocr import DefaultOCR
from utils.thai_plate_parser import parse_thai_plate

# pylint: disable=too-many-arguments, too-many-locals
# ruff: noqa: PLR0913


@dataclass(frozen=True)
class ALPRResult:
    """
    Dataclass to hold the results of detection and OCR for a license plate.
    
    Enhanced with Thai plate parsing information.
    """

    detection: DetectionResult
    ocr: OcrResult | None
    # Thai plate specific fields
    plate_category: str | None = None
    plate_number: str | None = None
    province: str | None = None


class ALPR:
    """
    Automatic License Plate Recognition (ALPR) system class.

    This class combines a detector and an OCR model to recognize license plates in images.
    Enhanced with Thai license plate parsing.
    """

    def __init__(
        self,
        detector: BaseDetector | None = None,
        ocr: BaseOCR | None = None,
        detector_model: PlateDetectorModel = "yolo-v9-t-384-license-plate-end2end",
        detector_conf_thresh: float = 0.4,
        detector_providers: Sequence[str | tuple[str, dict]] | None = None,
        detector_sess_options: ort.SessionOptions = None,
        ocr_model: OcrModel | None = "cct-xs-v1-global-model",
        ocr_device: Literal["cuda", "cpu", "auto"] = "auto",
        ocr_providers: Sequence[str | tuple[str, dict]] | None = None,
        ocr_sess_options: ort.SessionOptions | None = None,
        ocr_model_path: str | os.PathLike | None = None,
        ocr_config_path: str | os.PathLike | None = None,
        ocr_force_download: bool = False,
        parse_thai: bool = True,
    ) -> None:
        """
        Initialize the ALPR system.

        Parameters:
            detector: An instance of BaseDetector. If None, the DefaultDetector is used.
            ocr: An instance of BaseOCR. If None, the DefaultOCR is used.
            detector_model: The name of the detector model or a PlateDetectorModel enum instance.
            detector_conf_thresh: Confidence threshold for the detector.
            detector_providers: Execution providers for the detector.
            detector_sess_options: Session options for the detector.
            ocr_model: The name of the OCR model from the model hub.
            ocr_device: The device to run the OCR model on ("cuda", "cpu", or "auto").
            ocr_providers: Execution providers for the OCR.
            ocr_sess_options: Session options for the OCR.
            ocr_model_path: Custom model path for the OCR.
            ocr_config_path: Custom config path for the OCR.
            ocr_force_download: Whether to force download the OCR model.
            parse_thai: Whether to parse Thai license plate format.
        """
        # Initialize the detector
        self.detector = detector or DefaultDetector(
            model_name=detector_model,
            conf_thresh=detector_conf_thresh,
            providers=detector_providers,
            sess_options=detector_sess_options,
        )

        # Initialize the OCR with Thai parsing support
        self.ocr = ocr or DefaultOCR(
            hub_ocr_model=ocr_model,
            device=ocr_device,
            providers=ocr_providers,
            sess_options=ocr_sess_options,
            model_path=ocr_model_path,
            config_path=ocr_config_path,
            force_download=ocr_force_download,
            parse_thai=parse_thai,
        )
        self.parse_thai = parse_thai

    def predict(self, frame: np.ndarray | str) -> list[ALPRResult]:
        """
        Returns all recognized license plates from a frame.

        Parameters:
            frame: Unprocessed frame (Colors in order: BGR) or image path.

        Returns:
            A list of ALPRResult objects containing detection, OCR, and Thai plate info.
        """
        if isinstance(frame, str):
            img_path = frame
            img = cv2.imread(img_path)
            if img is None:
                raise ValueError(f"Failed to load image from path: {img_path}")
        else:
            img = frame

        plate_detections = self.detector.predict(img)
        alpr_results: list[ALPRResult] = []
        
        for detection in plate_detections:
            bbox = detection.bounding_box
            x1, y1 = max(bbox.x1, 0), max(bbox.y1, 0)
            x2, y2 = min(bbox.x2, img.shape[1]), min(bbox.y2, img.shape[0])
            cropped_plate = img[y1:y2, x1:x2]
            ocr_result = self.ocr.predict(cropped_plate)
            
            # Parse Thai plate information if enabled
            plate_category = None
            plate_number = None
            province = None
            
            if self.parse_thai and ocr_result and ocr_result.text:
                thai_info = parse_thai_plate(ocr_result.text)
                if thai_info:
                    plate_category = thai_info.category
                    plate_number = thai_info.number
                    province = thai_info.province
            
            alpr_result = ALPRResult(
                detection=detection,
                ocr=ocr_result,
                plate_category=plate_category,
                plate_number=plate_number,
                province=province,
            )
            alpr_results.append(alpr_result)
            
        return alpr_results

    def draw_predictions(self, frame: np.ndarray | str) -> np.ndarray:
        """
        Draws detections and OCR results on the frame.

        Parameters:
            frame: The original frame or image path.

        Returns:
            The frame with detections and OCR results drawn.
        """
        if isinstance(frame, str):
            img_path = frame
            img = cv2.imread(img_path)
            if img is None:
                raise ValueError(f"Failed to load image from path: {img_path}")
        else:
            img = frame

        alpr_results = self.predict(img)

        for result in alpr_results:
            detection = result.detection
            ocr_result = result.ocr
            bbox = detection.bounding_box
            x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
            
            # Draw the bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), (36, 255, 12), 2)
            
            if ocr_result is None or not ocr_result.text or not ocr_result.confidence:
                continue
                
            plate_text = ocr_result.text
            confidence: float = (
                statistics.mean(ocr_result.confidence)
                if isinstance(ocr_result.confidence, list)
                else ocr_result.confidence
            )
            display_text = f"{plate_text} {confidence * 100:.2f}%"
            font_scale = 1.25
            
            # Draw black background for better readability
            cv2.putText(
                img=img,
                text=display_text,
                org=(x1, y1 - 10),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=font_scale,
                color=(0, 0, 0),
                thickness=6,
                lineType=cv2.LINE_AA,
            )
            # Draw white text
            cv2.putText(
                img=img,
                text=display_text,
                org=(x1, y1 - 10),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=font_scale,
                color=(255, 255, 255),
                thickness=2,
                lineType=cv2.LINE_AA,
            )

        return img