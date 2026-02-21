"""Production dashboard for CCTV ALPR reports."""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st

st.set_page_config(page_title="FastALPR CCTV Dashboard", layout="wide")
st.title("📹 FastALPR CCTV Dashboard")

backend_url = os.getenv("BACKEND_URL", "http://alpr-backend-cpu:8080")
latest_endpoint = f"{backend_url.rstrip('/')}/latest"

st.caption(f"Backend: {latest_endpoint}")
refresh = st.button("Refresh report")
auto_refresh = st.toggle("Auto refresh (every 5s)", value=True)
if auto_refresh:
    st.markdown("<meta http-equiv='refresh' content='5'>", unsafe_allow_html=True)

if refresh or auto_refresh:
    try:
        with urlopen(latest_endpoint, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        st.error(f"Cannot connect to backend: {exc}")
        st.stop()

    left, right = st.columns(2)
    with left:
        st.metric("Status", payload.get("status", "unknown"))
        st.metric("Detected plates", payload.get("plates_detected", 0))
        st.write(f"Updated at: {payload.get('updated_at', '-')}")
        st.write(f"Source: {payload.get('source', '-')}")
    with right:
        st.subheader("Raw JSON")
        st.json(payload)

    detections = payload.get("detections", [])
    if detections:
        rows = []
        for idx, item in enumerate(detections, start=1):
            bbox = item["detection"]["bounding_box"]
            rows.append(
                {
                    "id": idx,
                    "label": item["detection"]["label"],
                    "detection_confidence": round(item["detection"]["confidence"], 4),
                    "ocr_text": (item.get("ocr") or {}).get("text", ""),
                    "ocr_confidence": (item.get("ocr") or {}).get("confidence", ""),
                    "x1": bbox["x1"],
                    "y1": bbox["y1"],
                    "x2": bbox["x2"],
                    "y2": bbox["y2"],
                }
            )
        st.subheader("Detection Report")
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No detections yet.")
