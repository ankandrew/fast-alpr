"""Production dashboard for Thai ALPR CCTV with database integration and manual review."""

from __future__ import annotations

import json
import os
from io import BytesIO
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st
from PIL import Image

st.set_page_config(page_title="Thai ALPR Dashboard", layout="wide")
st.title("🇹🇭 Thai ALPR & Data Management Dashboard")

backend_url = os.getenv("BACKEND_URL", "http://alpr-backend:8000")
latest_endpoint = f"{backend_url.rstrip('/')}/latest"
logs_endpoint = f"{backend_url.rstrip('/')}/logs"
verify_endpoint = f"{backend_url.rstrip('/')}/verify"
stats_endpoint = f"{backend_url.rstrip('/')}/stats"

st.caption(f"Backend: {backend_url}")

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Manual refresh button
    refresh_button = st.button("🔄 Refresh Now", use_container_width=True)
    
    # Auto-refresh toggle
    auto_refresh = st.toggle("🔁 Auto Refresh (5s)", value=True)
    
    # Filter controls
    st.subheader("🔍 Filters")
    status_filter = st.selectbox(
        "Status Filter",
        options=["All", "PENDING", "ALPR", "MLPR"],
        index=0,
    )
    
    # Record limit
    record_limit = st.slider("Records to display", min_value=10, max_value=200, value=50, step=10)

# Auto-refresh logic
if auto_refresh:
    st.markdown("<meta http-equiv='refresh' content='5'>", unsafe_allow_html=True)

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📊 Live Status", "📋 Database Records", "📈 Statistics"])

# Tab 1: Live Status (existing functionality)
with tab1:
    st.header("Live CCTV Status")
    
    if refresh_button or auto_refresh:
        try:
            with urlopen(latest_endpoint, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            st.error(f"❌ Cannot connect to backend: {exc}")
            st.stop()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("System Status", payload.get("status", "unknown"))
        with col2:
            st.metric("Plates Detected", payload.get("plates_detected", 0))
        with col3:
            st.write(f"**Updated:** {payload.get('updated_at', '-')}")

        st.write(f"**Source:** {payload.get('source', '-')}")

        detections = payload.get("detections", [])
        if detections:
            st.subheader("Recent Detections")
            rows = []
            for idx, item in enumerate(detections, start=1):
                thai_plate = item.get("thai_plate", {})
                ocr_data = item.get("ocr", {})
                
                rows.append({
                    "DB ID": item.get("db_id", "-"),
                    "Category": thai_plate.get("category", "-"),
                    "Number": thai_plate.get("number", "-"),
                    "Province": thai_plate.get("province", "-"),
                    "Confidence": f"{ocr_data.get('confidence', 0):.2%}" if ocr_data else "-",
                    "Status": item.get("status", "-"),
                })
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("ℹ️ No recent detections")

# Tab 2: Database Records with Manual Review
with tab2:
    st.header("Database Records & Manual Review")
    
    try:
        # Fetch logs from backend
        filter_param = "" if status_filter == "All" else f"?status={status_filter}"
        logs_url = f"{logs_endpoint}{filter_param}&limit={record_limit}"
        
        with urlopen(logs_url, timeout=10) as response:
            logs = json.loads(response.read().decode("utf-8"))
        
        if not logs:
            st.info(f"ℹ️ No records found with status: {status_filter}")
        else:
            st.write(f"**Showing {len(logs)} records**")
            
            # Display records with review capability
            for idx, log in enumerate(logs):
                with st.expander(
                    f"🚗 Record #{log['id']} - {log.get('plate_category', '')} {log.get('plate_number', '')} "
                    f"({log['status']}) - Confidence: {log.get('confidence', 0):.2%}",
                    expanded=(idx == 0 and status_filter == "PENDING"),  # Auto-expand first pending
                ):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Display crop image
                        st.subheader("📸 Plate Image")
                        crop_path = log.get("crop_path")
                        
                        if crop_path and os.path.exists(crop_path):
                            try:
                                image = Image.open(crop_path)
                                st.image(image, caption="Cropped Plate", use_container_width=True)
                            except Exception as e:
                                st.error(f"Cannot load image: {e}")
                        else:
                            st.warning("Image not found")
                        
                        # Show metadata
                        st.write(f"**Time:** {log.get('timestamp', '-')}")
                        st.write(f"**Confidence:** {log.get('confidence', 0):.2%}")
                        st.write(f"**Status:** {log.get('status', '-')}")
                        st.write(f"**Raw Text:** {log.get('raw_text', '-')}")
                    
                    with col2:
                        st.subheader("✏️ Review & Edit")
                        
                        # Create unique keys for each form
                        form_key = f"review_form_{log['id']}"
                        
                        with st.form(key=form_key):
                            # Editable fields
                            category = st.text_input(
                                "Plate Category",
                                value=log.get("plate_category", ""),
                                key=f"cat_{log['id']}",
                                help="e.g., 1กก, 2กก, นย",
                            )
                            
                            number = st.text_input(
                                "Plate Number",
                                value=log.get("plate_number", ""),
                                key=f"num_{log['id']}",
                                help="e.g., 1234",
                            )
                            
                            province = st.text_input(
                                "Province",
                                value=log.get("province", ""),
                                key=f"prov_{log['id']}",
                                help="e.g., กรุงเทพมหานคร",
                            )
                            
                            # Preview
                            st.write(f"**Preview:** {category} {number} {province}")
                            
                            # Submit button
                            submit = st.form_submit_button("✅ Verify & Save to Training Set", use_container_width=True)
                            
                            if submit:
                                if not category or not number:
                                    st.error("⚠️ Category and Number are required!")
                                else:
                                    # Send verification request to backend
                                    try:
                                        verify_data = json.dumps({
                                            "log_id": log["id"],
                                            "plate_category": category,
                                            "plate_number": number,
                                            "province": province,
                                        }).encode("utf-8")
                                        
                                        req = urlopen(
                                            verify_endpoint,
                                            data=verify_data,
                                            timeout=10,
                                        )
                                        
                                        result = json.loads(req.read().decode("utf-8"))
                                        
                                        if result.get("success"):
                                            st.success(f"✅ {result.get('message')}")
                                            st.balloons()
                                            # Force refresh
                                            st.rerun()
                                        else:
                                            st.error(f"❌ Verification failed: {result}")
                                    
                                    except Exception as e:
                                        st.error(f"❌ Error during verification: {e}")
    
    except URLError as e:
        st.error(f"❌ Cannot fetch logs from backend: {e}")
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Tab 3: Statistics & KPIs
with tab3:
    st.header("System Statistics & KPIs")
    
    try:
        with urlopen(stats_endpoint, timeout=5) as response:
            stats = json.loads(response.read().decode("utf-8"))
        
        # Display KPIs in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Records", stats.get("total_logs", 0))
        
        with col2:
            st.metric("⏳ Pending Review", stats.get("pending_review", 0))
        
        with col3:
            st.metric("🤖 Auto-Detected (ALPR)", stats.get("auto_detected", 0))
        
        with col4:
            st.metric("✅ Manually Verified (MLPR)", stats.get("manually_verified", 0))
        
        # Accuracy metric (prominent display)
        st.markdown("---")
        accuracy = stats.get("accuracy_percentage", 0.0)
        
        # Color-code accuracy
        if accuracy >= 90:
            color = "green"
        elif accuracy >= 70:
            color = "orange"
        else:
            color = "red"
        
        st.markdown(
            f"<h2 style='text-align: center; color: {color};'>🎯 System Accuracy: {accuracy:.2f}%</h2>",
            unsafe_allow_html=True,
        )
        
        st.caption("Accuracy = (Auto-Detected + Manually Verified) / Total Records")
        
        # Progress bars
        st.markdown("---")
        st.subheader("Status Breakdown")
        
        total = stats.get("total_logs", 1)  # Avoid division by zero
        
        st.write("**ALPR (Auto-Detected)**")
        st.progress(stats.get("auto_detected", 0) / total)
        
        st.write("**MLPR (Manually Verified)**")
        st.progress(stats.get("manually_verified", 0) / total)
        
        st.write("**PENDING (Needs Review)**")
        st.progress(stats.get("pending_review", 0) / total)
        
    except URLError as e:
        st.error(f"❌ Cannot fetch statistics: {e}")
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Footer
st.markdown("---")
st.caption("Thai ALPR System v2.0 - Powered by FastALPR with PostgreSQL Integration")