"""
Default OCR module with Thai license plate support.
"""

import os
from collections.abc import Sequence
from typing import Literal

import cv2
import numpy as np
import onnxruntime as ort
from fast_plate_ocr import LicensePlateRecognizer
from fast_plate_ocr.inference.hub import OcrModel

from fast_alpr.base import BaseOCR, OcrResult
from utils.thai_plate_parser import parse_thai_plate


class DefaultOCR(BaseOCR):
    """
    Default OCR class for license plate recognition using ONNX models.
    
    Enhanced with Thai license plate parsing capabilities.
    """

    def __init__(
        self,
        hub_ocr_model: OcrModel | None = None,
        device: Literal["cuda", "cpu", "auto"] = "auto",
        providers: Sequence[str | tuple[str, dict]] | None = None,
        sess_options: ort.SessionOptions | None = None,
        model_path: str | os.PathLike | None = None,
        config_path: str | os.PathLike | None = None,
        force_download: bool = False,
        parse_thai: bool = True,
    ) -> None:
        """
        Initialize the DefaultOCR with the specified parameters.

        Parameters:
            hub_ocr_model: The name of the OCR model from the model hub.
            device: The device to run the model on. Options are "cuda", "cpu", or "auto".
            providers: The execution providers to use in ONNX Runtime.
            sess_options: Custom session options for ONNX Runtime.
            model_path: Path to a custom OCR model file.
            config_path: Path to a custom configuration file.
            force_download: If True, forces the download of the model.
            parse_thai: If True, parse Thai license plate format.
        """
        self.ocr_model = LicensePlateRecognizer(
            hub_ocr_model=hub_ocr_model,
            device=device,
            providers=providers,
            sess_options=sess_options,
            onnx_model_path=model_path,
            plate_config_path=config_path,
            force_download=force_download,
        )
        self.parse_thai = parse_thai

    def predict(self, cropped_plate: np.ndarray) -> OcrResult | None:
        """
        Perform OCR on a cropped license plate image.
        
        For Thai plates, attempts to parse the format into category, number, and province.

        Parameters:
            cropped_plate: The cropped image of the license plate in BGR format.

        Returns:
            OcrResult with text and confidence. For Thai plates, text may be formatted.
        """
        if cropped_plate is None:
            return None
            
        if self.ocr_model.config.image_color_mode == "grayscale":
            cropped_plate = cv2.cvtColor(cropped_plate, cv2.COLOR_BGR2GRAY)
            
        plate_text, probabilities = self.ocr_model.run(cropped_plate, return_confidence=True)
        
        if not isinstance(plate_text, list):
            raise TypeError(f"Expected plate_text to be a list, got {type(plate_text).__name__}")
        if not isinstance(probabilities, np.ndarray):
            raise TypeError(
                f"Expected probabilities to be a numpy ndarray, got {type(probabilities).__name__}"
            )
            
        # fast_plate_ocr uses '_' padding symbol
        plate_text_str = plate_text.pop().replace("_", "")
        avg_confidence = float(np.mean(probabilities))
        
        # For Thai plates, attempt to parse the format
        if self.parse_thai:
            thai_info = parse_thai_plate(plate_text_str)
            if thai_info:
                # Store parsed info in a structured way
                # The text field will contain the formatted version
                formatted_text = f"{thai_info.category} {thai_info.number} {thai_info.province}".strip()
                if formatted_text:
                    plate_text_str = formatted_text
        
        return OcrResult(text=plate_text_str, confidence=avg_confidence)