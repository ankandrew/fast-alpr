# 🇹🇭 Thai ALPR & Data Management System

A production-ready Thai Automatic License Plate Recognition (ALPR) system with PostgreSQL database integration, manual verification workflow, and training dataset management.

## 🌟 New Features (v2.0)

- **🗄️ PostgreSQL Integration**: All detections stored in database with full audit trail
- **🇹🇭 Thai License Plate Support**: Automatic parsing of Thai plate format (Category + Number + Province)
- **✅ Manual Verification**: Review and correct low-confidence detections via web dashboard
- **📚 Training Dataset Management**: Verified plates automatically added to training dataset
- **📊 Accuracy KPIs**: Real-time system accuracy tracking and statistics
- **🎯 Smart Status Management**: Auto-classify detections as PENDING/ALPR/MLPR based on confidence

## 📋 Thai License Plate Format

The system parses Thai plates in the format:
```
[Category] [Number] [Province]
```

Examples:
- `1กก 1234 กรุงเทพมหานคร`
- `2กก 5678 เชียงใหม่`
- `นย 9999 ภูเก็ต`

## 🐳 Quick Start with Docker Compose

### 1. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 2. Run with CPU (Development)

```bash
docker compose up -d postgres alpr-backend alpr-frontend
```

### 3. Run with GPU (Production - NVIDIA GPUs)

```bash
CCTV_SOURCE="rtsp://user:password@camera-ip:554/stream1" docker compose up -d
```

### 4. Access the System

- **Backend API**: http://localhost:8000/docs (Swagger UI)
- **Frontend Dashboard**: http://localhost:3000
- **Database**: localhost:5432

## 📊 System Architecture

```
┌─────────────────┐
│  CCTV Source    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  ALPR Backend   │─────▶│  PostgreSQL  │
│  (FastAPI)      │      │   Database   │
└────────┬────────┘      └──────────────┘
         │
         │ HTTP API
         │
         ▼
┌─────────────────┐
│  Web Dashboard  │
│  (Streamlit)    │
└─────────────────┘
```

## 🗄️ Database Schema

```sql
CREATE TABLE vehicle_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    image_path VARCHAR NOT NULL,           -- Full frame image
    crop_path VARCHAR NOT NULL,            -- Cropped plate image
    plate_category VARCHAR,                -- e.g., "1กก"
    plate_number VARCHAR,                  -- e.g., "1234"
    province VARCHAR,                      -- e.g., "กรุงเทพมหานคร"
    confidence FLOAT NOT NULL,             -- OCR confidence
    status VARCHAR NOT NULL,               -- PENDING/ALPR/MLPR
    raw_text VARCHAR,                      -- Original OCR output
    detection_confidence FLOAT,            -- Detection confidence
    bounding_box VARCHAR                   -- JSON bbox coordinates
);
```

## 📁 Directory Structure

```
./artifacts/
  ├── images/           # Full frame images
  ├── crops/            # Cropped plate images
  ├── latest_report.json
  ├── latest_frame.jpg
  └── events.jsonl

./dataset/
  └── training/         # Verified plates for training
      └── YYYYMMDD_HHMMSS_[plate]_[id].jpg
```

## 🔄 Processing Workflow

1. **CCTV Frame Capture** → Every Nth frame (configurable via `FRAME_STRIDE`)
2. **License Plate Detection** → YOLO-based detector
3. **OCR & Thai Parsing** → Extract category, number, province
4. **Auto-Classification**:
   - Confidence ≥ 95% → Status: `ALPR` (Auto-accepted)
   - Confidence < 95% → Status: `PENDING` (Needs review)
5. **Manual Review** (Optional):
   - Human corrects via dashboard
   - Status changes to `MLPR`
   - Crop saved to training dataset
6. **Database Storage** → Full audit trail

## 🌐 API Endpoints

### Core Endpoints

- `GET /health` - System health check
- `GET /latest` - Latest detection report
- `GET /logs?status=PENDING&limit=100` - Query database records
- `POST /verify` - Manually verify a record
- `GET /stats` - System statistics and KPIs

### Example: Manual Verification

```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": 123,
    "plate_category": "1กก",
    "plate_number": "1234",
    "province": "กรุงเทพมหานคร"
  }'
```

## 📈 Dashboard Features

### Live Status Tab
- Real-time CCTV stream status
- Recent detections with Thai plate parsing
- Confidence scores and classification status

### Database Records Tab
- **Filter by status**: PENDING / ALPR / MLPR
- **Visual review**: See cropped plate images
- **Edit & verify**: Correct category, number, province
- **One-click training**: Verified plates → training dataset

### Statistics Tab
- Total records processed
- Pending reviews count
- Auto-detected (ALPR) count
- Manually verified (MLPR) count
- **System Accuracy KPI**: (ALPR + MLPR) / Total

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CCTV_SOURCE` | RTSP stream or image path | `assets/test_image.png` |
| `FRAME_STRIDE` | Process every Nth frame | `5` |
| `HIGH_CONFIDENCE_THRESHOLD` | Auto-accept threshold | `0.95` |
| `DATABASE_URL` | PostgreSQL connection string | See `.env.example` |
| `DETECTOR_MODEL` | Plate detection model | `yolo-v9-t-384-license-plate-end2end` |
| `OCR_MODEL` | OCR model | `cct-xs-v1-global-model` |

### GPU Configuration

For NVIDIA GPUs, the system automatically uses CUDA if available:

```bash
# In docker-compose.yml, services already configured with:
gpus: all
environment:
  NVIDIA_VISIBLE_DEVICES: all
  NVIDIA_DRIVER_CAPABILITIES: compute,utility
```

## 🔧 Development

### Running Tests

```bash
make install
make checks
```

### Database Migrations

```bash
# Connect to database
docker exec -it <postgres_container> psql -U alpr_user -d thai_alpr

# View tables
\dt

# Query records
SELECT id, plate_category, plate_number, province, status, confidence 
FROM vehicle_logs 
ORDER BY timestamp DESC 
LIMIT 10;
```

## 📊 Monitoring & Analytics

### View System Stats

```bash
curl http://localhost:8000/stats
```

Response:
```json
{
  "total_logs": 1250,
  "pending_review": 45,
  "auto_detected": 1150,
  "manually_verified": 55,
  "accuracy_percentage": 96.4
}
```

### Event Stream (JSONL)

All events are logged to `artifacts/events.jsonl` for analysis:

```bash
tail -f artifacts/events.jsonl | jq .
```

## 🚀 Production Deployment

### Resource Requirements

- **CPU Mode**: 2 cores, 4GB RAM minimum
- **GPU Mode**: NVIDIA GPU with 4GB+ VRAM, 8GB RAM
- **Database**: 1GB storage for ~100k records

### Performance Tuning

1. **Adjust Frame Stride**: Higher values = faster processing, fewer records
   ```bash
   FRAME_STRIDE=10  # Process every 10th frame
   ```

2. **Confidence Threshold**: Lower values = more auto-accepts
   ```bash
   HIGH_CONFIDENCE_THRESHOLD=0.90
   ```

3. **Database Connection Pool**: Edit `service/cctv_api.py` for high load

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# View logs
docker compose logs postgres
```

### Images Not Displaying in Dashboard
```bash
# Ensure correct volume mounts
docker compose down
docker compose up -d

# Check file permissions
ls -la artifacts/crops/
```

### Low Accuracy
1. Review PENDING records via dashboard
2. Manually verify and build training dataset
3. Retrain OCR model with verified data (see documentation)

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! See `docs/contributing.md` for guidelines.

---

**v2.0** - Thai ALPR System with PostgreSQL Integration