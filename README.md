# FastALPR

[![Actions status](https://github.com/ankandrew/fast-alpr/actions/workflows/test.yaml/badge.svg)](https://github.com/ankandrew/fast-alpr/actions)
[![Actions status](https://github.com/ankandrew/fast-alpr/actions/workflows/release.yaml/badge.svg)](https://github.com/ankandrew/fast-alpr/actions)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![ONNX Model](https://img.shields.io/badge/model-ONNX-blue?logo=onnx&logoColor=white)](https://onnx.ai/)
[![Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces-orange)](https://huggingface.co/spaces/ankandrew/fast-alpr)
[![Documentation Status](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://ankandrew.github.io/fast-alpr/)
[![Python Version](https://img.shields.io/pypi/pyversions/fast-alpr)](https://www.python.org/)
[![GitHub version](https://img.shields.io/github/v/release/ankandrew/fast-alpr)](https://github.com/ankandrew/fast-alpr/releases)
[![License](https://img.shields.io/github/license/ankandrew/fast-alpr)](./LICENSE)

[![ALPR Demo Animation](https://raw.githubusercontent.com/ankandrew/fast-alpr/f672fbbec2ddf86aabfc2afc0c45d1fa7612516c/assets/alpr.gif)](https://youtu.be/-TPJot7-HTs?t=652)

**FastALPR** is a high-performance, customizable Automatic License Plate Recognition (ALPR) system. We offer fast and
efficient ONNX models by default, but you can easily swap in your own models if needed.

For Optical Character Recognition (**OCR**), we use [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr) by
default, and for **license plate detection**, we
use [open-image-models](https://github.com/ankandrew/open-image-models). However, you can integrate any OCR or detection
model of your choice.

## 📋 Table of Contents

* [✨ Features](#-features)
* [📦 Installation](#-installation)
* [🚀 Quick Start](#-quick-start)
* [🛠️ Customization and Flexibility](#-customization-and-flexibility)
* [📖 Documentation](#-documentation)
* [🤝 Contributing](#-contributing)
* [🙏 Acknowledgements](#-acknowledgements)
* [📫 Contact](#-contact)

## ✨ Features

- **High Accuracy**: Uses advanced models for precise license plate detection and OCR.
- **Customizable**: Easily switch out detection and OCR models.
- **Easy to Use**: Quick setup with a simple API.
- **Out-of-the-Box Models**: Includes ready-to-use detection and OCR models
- **Fast Performance**: Optimized with ONNX Runtime for speed.

## 📦 Installation

```shell
pip install fast-alpr[onnx-gpu]
```

By default, **no ONNX runtime is installed**. To run inference, you **must** install at least one ONNX backend using an appropriate extra.

| Platform/Use Case  | Install Command                        | Notes                |
|--------------------|----------------------------------------|----------------------|
| CPU (default)      | `pip install fast-alpr[onnx]`          | Cross-platform       |
| NVIDIA GPU (CUDA)  | `pip install fast-alpr[onnx-gpu]`      | Linux/Windows        |
| Intel (OpenVINO)   | `pip install fast-alpr[onnx-openvino]` | Best on Intel CPUs   |
| Windows (DirectML) | `pip install fast-alpr[onnx-directml]` | For DirectML support |
| Qualcomm (QNN)     | `pip install fast-alpr[onnx-qnn]`      | Qualcomm chipsets    |


## 🚀 Quick Start

> [!TIP]
> Try `fast-alpr` in [Hugging Spaces](https://huggingface.co/spaces/ankandrew/fast-alpr).

Here's how to get started with FastALPR:

```python
from fast_alpr import ALPR

# You can also initialize the ALPR with custom plate detection and OCR models.
alpr = ALPR(
    detector_model="yolo-v9-t-384-license-plate-end2end",
    ocr_model="cct-xs-v1-global-model",
)

# The "assets/test_image.png" can be found in repo root dir
alpr_results = alpr.predict("assets/test_image.png")
print(alpr_results)
```

Output:

<img alt="ALPR Result" src="https://raw.githubusercontent.com/ankandrew/fast-alpr/5063bd92fdd30f46b330d051468be267d4442c9b/assets/alpr_result.webp"/>

You can also draw the predictions directly on the image:

```python
import cv2

from fast_alpr import ALPR

# Initialize the ALPR
alpr = ALPR(
    detector_model="yolo-v9-t-384-license-plate-end2end",
    ocr_model="cct-xs-v1-global-model",
)

# Load the image
image_path = "assets/test_image.png"
frame = cv2.imread(image_path)

# Draw predictions on the image
annotated_frame = alpr.draw_predictions(frame)
```

Annotated frame:

<img alt="ALPR Draw Predictions" src="https://raw.githubusercontent.com/ankandrew/fast-alpr/0a6076dcb8d9084514fe47e8abaaeb77cae45f8e/assets/alpr_draw_predictions.png"/>

## 🛠️ Customization and Flexibility

FastALPR is designed to be flexible. You can customize the detector and OCR models according to your requirements.
You can very easily integrate with **Tesseract** OCR to leverage its capabilities:

```python
import re
from statistics import mean

import numpy as np
import pytesseract

from fast_alpr.alpr import ALPR, BaseOCR, OcrResult


class PytesseractOCR(BaseOCR):
    def __init__(self) -> None:
        """
        Init PytesseractOCR.
        """

    def predict(self, cropped_plate: np.ndarray) -> OcrResult | None:
        if cropped_plate is None:
            return None
        # You can change 'eng' to the appropriate language code as needed
        data = pytesseract.image_to_data(
            cropped_plate,
            lang="eng",
            config="--oem 3 --psm 6",
            output_type=pytesseract.Output.DICT,
        )
        plate_text = " ".join(data["text"]).strip()
        plate_text = re.sub(r"[^A-Za-z0-9]", "", plate_text)
        avg_confidence = mean(conf for conf in data["conf"] if conf > 0) / 100.0
        return OcrResult(text=plate_text, confidence=avg_confidence)


alpr = ALPR(detector_model="yolo-v9-t-384-license-plate-end2end", ocr=PytesseractOCR())

alpr_results = alpr.predict("assets/test_image.png")
print(alpr_results)
```

> [!TIP]
> See the [docs](https://ankandrew.github.io/fast-alpr/) for more examples!

## 📖 Documentation

Comprehensive documentation is available [here](https://ankandrew.github.io/fast-alpr/), including detailed API
references and additional examples.


## 🐳 Docker Compose (Test)

Run the test suite in Docker (CPU):

```shell
docker compose run --rm alpr-test-cpu
```

Run the test suite with NVIDIA GPU (e.g. RTX 3060):

```shell
docker compose --profile gpu run --rm alpr-test-gpu
```

> [!NOTE]
> GPU mode requires NVIDIA Container Toolkit on the host and a recent Docker Compose version that supports `gpus: all`.

## 🤝 Contributing

Contributions to the repo are greatly appreciated. Whether it's bug fixes, feature enhancements, or new models,
your contributions are warmly welcomed.

To start contributing or to begin development, you can follow these steps:

1. Clone repo
    ```shell
    git clone https://github.com/ankandrew/fast-alpr.git
    ```
2. Install all dependencies (make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed):
    ```shell
    make install
    ```
3. To ensure your changes pass linting and tests before submitting a PR:
    ```shell
    make checks
    ```

## 🙏 Acknowledgements

- [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr) for default **OCR** models.
- [open-image-models](https://github.com/ankandrew/open-image-models) for default plate **detection** models.

## 📫 Contact

For questions or suggestions, feel free to open an issue.
