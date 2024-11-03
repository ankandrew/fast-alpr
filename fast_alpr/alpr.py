"""
ALPR module.
"""

import os
from collections.abc import Sequence
from typing import Literal

import cv2
import numpy as np
import onnxruntime as ort
from fast_plate_ocr.inference.hub import OcrModel
from open_image_models.detection.core.hub import PlateDetectorModel

from fast_alpr.base import BaseDetector, BaseOCR
from fast_alpr.default_detector import DefaultDetector
from fast_alpr.default_ocr import DefaultOCR

# pylint: disable=too-many-arguments
# ruff: noqa: PLR0913


class ALPR:
    """
    Automatic License Plate Recognition (ALPR) system class.

    This class combines a detector and an OCR model to recognize license plates in images.
    """

    def __init__(
        self,
        detector: BaseDetector | None = None,
        ocr: BaseOCR | None = None,
        detector_model: PlateDetectorModel = "yolo-v9-t-384-license-plate-end2end",
        detector_conf_thresh: float = 0.4,
        detector_providers: Sequence[str | tuple[str, dict]] | None = None,
        detector_sess_options: ort.SessionOptions = None,
        ocr_hub_ocr_model: OcrModel | None = "european-plates-mobile-vit-v2-model",
        ocr_device: Literal["cuda", "cpu", "auto"] = "auto",
        ocr_providers: Sequence[str | tuple[str, dict]] | None = None,
        ocr_sess_options: ort.SessionOptions | None = None,
        ocr_model_path: str | os.PathLike | None = None,
        ocr_config_path: str | os.PathLike | None = None,
        ocr_force_download: bool = False,
    ) -> None:
        """
        Initialize the ALPR system.

        Parameters:
            detector: An instance of BaseDetector. If None, the DefaultDetector is used.
            ocr: An instance of BaseOCR. If None, the DefaultOCR is used.
            detector_model: The name of the detector model or a PlateDetectorModel enum instance.
                Defaults to "yolo-v9-t-384-license-plate-end2end".
            detector_conf_thresh: Confidence threshold for the detector.
            detector_providers: Execution providers for the detector.
            detector_sess_options: Session options for the detector.
            ocr_hub_ocr_model: The name of the OCR model from the model hub. This can be none and
                `ocr_model_path` and `ocr_config_path` parameters are expected to pass them to
                `fast-plate-ocr` library.
            ocr_device: The device to run the OCR model on ("cuda", "cpu", or "auto").
            ocr_providers: Execution providers for the OCR. If None, the default providers are used.
            ocr_sess_options: Session options for the OCR. If None, default session options are
             used.
            ocr_model_path: Custom model path for the OCR. If None, the model is downloaded from the
                hub or cache.
            ocr_config_path: Custom config path for the OCR. If None, the default configuration is
                used.
            ocr_force_download: Whether to force download the OCR model.
        """
        # Initialize the detector
        self.detector = detector or DefaultDetector(
            model_name=detector_model,
            conf_thresh=detector_conf_thresh,
            providers=detector_providers,
            sess_options=detector_sess_options,
        )

        # Initialize the OCR
        self.ocr = ocr or DefaultOCR(
            hub_ocr_model=ocr_hub_ocr_model,
            device=ocr_device,
            providers=ocr_providers,
            sess_options=ocr_sess_options,
            model_path=ocr_model_path,
            config_path=ocr_config_path,
            force_download=ocr_force_download,
        )

    def predict(self, frame: np.ndarray) -> list[str]:
        """
        Returns all recognized license plates from a frame.

        Parameters:
            frame: Unprocessed frame (Colors in order: BGR).

        Returns:
            A list of all recognized license plates.
        """
        plate_detections = self.detector.predict(frame)
        recognized_plates = []
        for detection in plate_detections:
            bbox = detection.bounding_box
            x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
            cropped_plate = frame[y1:y2, x1:x2]
            ocr_result = self.ocr.predict(cropped_plate)
            if ocr_result is None or not ocr_result.text or not ocr_result.confidences:
                continue
            # Remove padding symbols if any
            plate_text = ocr_result.text.replace(ocr_result.padding_symbol or "", "")
            recognized_plates.append(plate_text)
        return recognized_plates

    def draw_predictions(self, frame: np.ndarray) -> np.ndarray:
        """
        Draws detections and OCR results on the frame.

        Parameters:
            frame: The original frame.

        Returns:
            The frame with detections and OCR results drawn.
        """
        plate_detections = self.detector.predict(frame)
        for detection in plate_detections:
            bbox = detection.bounding_box
            x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
            # Draw the bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (36, 255, 12), 2)
            # Perform OCR on the cropped plate
            cropped_plate = frame[y1:y2, x1:x2]
            ocr_result = self.ocr.predict(cropped_plate)
            if ocr_result is None or not ocr_result.text or not ocr_result.confidences:
                continue
            # Remove padding symbols if any
            plate_text = ocr_result.text.replace(ocr_result.padding_symbol or "", "")
            avg_confidence = np.mean(ocr_result.confidences)
            display_text = f"{plate_text} {avg_confidence * 100:.2f}%"
            font_scale = 1.25
            # Draw black background for better readability
            cv2.putText(
                img=frame,
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
                img=frame,
                text=display_text,
                org=(x1, y1 - 10),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=font_scale,
                color=(255, 255, 255),
                thickness=2,
                lineType=cv2.LINE_AA,
            )
        return frame
