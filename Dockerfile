ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app

COPY . .

ARG ALPR_EXTRAS=onnx
RUN python -m pip install --upgrade pip \
    && python -m pip install ".[${ALPR_EXTRAS}]" fastapi uvicorn streamlit

CMD ["uvicorn", "service.cctv_api:app", "--host", "0.0.0.0", "--port", "8080"]
