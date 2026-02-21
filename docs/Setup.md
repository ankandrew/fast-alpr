# 🚀 Setup Guide - Thai ALPR System

## Prerequisites

- Docker & Docker Compose (for container deployment)
- OR Python 3.10+ (for local development)
- PostgreSQL 15+ (if running outside Docker)
- NVIDIA GPU + CUDA drivers (optional, for GPU acceleration)

## Option 1: Docker Compose (Recommended)

### Step 1: Clone and Configure

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
# Set your CCTV_SOURCE, database credentials, etc.
```

### Step 2: Start Services

```bash
# Start all services (PostgreSQL + Backend + Frontend)
docker compose up -d

# Check logs
docker compose logs -f alpr-backend
```

### Step 3: Access Dashboard

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

### Step 4: Test Detection

Place a test image in `assets/` or configure RTSP stream in `.env`, then check the dashboard.

## Option 2: Local Development

### Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install ALPR package
pip install -e ".[onnx]"  # CPU
# OR
pip install -e ".[onnx-gpu]"  # GPU

# Install database dependencies
pip install -r requirements-db.txt
```

### Step 2: Setup PostgreSQL

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE thai_alpr;
CREATE USER alpr_user WITH PASSWORD 'alpr_password';
GRANT ALL PRIVILEGES ON DATABASE thai_alpr TO alpr_user;
\q
```

### Step 3: Initialize Database

```bash
# Set database URL
export DATABASE_URL="postgresql://alpr_user:alpr_password@localhost:5432/thai_alpr"

# Run initialization script
python scripts/init_db.py
```

### Step 4: Run Backend

```bash
# Configure environment
export CCTV_SOURCE="assets/test_image.png"
export ARTIFACT_DIR="./artifacts"
export DATASET_DIR="./dataset"

# Start backend
uvicorn service.cctv_api:app --host 0.0.0.0 --port 8000
```

### Step 5: Run Frontend (in another terminal)

```bash
# Activate same virtual environment
source venv/bin/activate

# Set backend URL
export BACKEND_URL="http://localhost:8000"

# Start frontend
streamlit run frontend/app.py --server.port 3000
```

## Configuration Tips

### 1. RTSP Camera Setup

```bash
# In .env file
CCTV_SOURCE=rtsp://admin:password@192.168.1.100:554/stream1
```

### 2. Adjust Processing Speed

```bash
# Process every 10th frame (faster, fewer records)
FRAME_STRIDE=10

# Process every frame (slower, all frames captured)
FRAME_STRIDE=1
```

### 3. Confidence Threshold

```bash
# More strict auto-acceptance (fewer ALPR, more PENDING)
HIGH_CONFIDENCE_THRESHOLD=0.98

# More lenient auto-acceptance (more ALPR, fewer PENDING)
HIGH_CONFIDENCE_THRESHOLD=0.90
```

### 4. GPU Configuration

The system automatically detects and uses GPU if available. To force CPU:

```bash
export ONNX_PROVIDERS="CPUExecutionProvider"
```

## Testing the System

### 1. Test API Health

```bash
curl http://localhost:8000/health
```

### 2. View Latest Detection

```bash
curl http://localhost:8000/latest | jq .
```

### 3. Query Database Records

```bash
curl http://localhost:8000/logs?status=PENDING&limit=10 | jq .
```

### 4. Get System Statistics

```bash
curl http://localhost:8000/stats | jq .
```

### 5. Manual Verification

```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": 1,
    "plate_category": "1กก",
    "plate_number": "1234",
    "province": "กรุงเทพมหานคร"
  }' | jq .
```

## Directory Structure After Setup

```
thai-alpr/
├── artifacts/              # Runtime data
│   ├── images/            # Full frame images
│   ├── crops/             # Cropped plates
│   ├── latest_report.json
│   ├── latest_frame.jpg
│   └── events.jsonl
├── dataset/
│   └── training/          # Verified plates for training
├── database/              # Database models
├── fast_alpr/             # Core ALPR package
├── service/               # Backend API
├── frontend/              # Dashboard
├── scripts/               # Utility scripts
├── utils/                 # Thai plate parser
├── docker-compose.yml
├── Dockerfile
└── .env
```

## Common Issues

### Issue: Cannot connect to database

```bash
# Check PostgreSQL status
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres
```

### Issue: Images not displaying

```bash
# Check volume mounts
docker compose down
docker compose up -d

# Verify file permissions
ls -la artifacts/crops/
```

### Issue: Low detection accuracy

1. Check OCR model configuration
2. Review PENDING records and manually verify
3. Ensure lighting conditions are good
4. Adjust detector confidence threshold

### Issue: High memory usage

```bash
# Reduce batch processing
FRAME_STRIDE=20

# Limit database query size
# In frontend, reduce record_limit slider
```

## Next Steps

1. **Monitor System**: Watch dashboard at http://localhost:3000
2. **Review Pending Records**: Click "Database Records" tab
3. **Verify Low-Confidence Plates**: Use the edit form to correct
4. **Build Training Dataset**: Verified plates automatically saved
5. **Track Accuracy**: Monitor Statistics tab for KPIs

## Production Deployment

For production deployment:

1. Use strong database passwords
2. Configure SSL/TLS for PostgreSQL
3. Set up backup for database and artifacts
4. Configure log rotation for events.jsonl
5. Monitor disk usage (images + database)
6. Set up alerts for pending review queue

## Support

- Report issues: GitHub Issues
- Check logs: `docker compose logs -f`
- View database: `psql` client or pgAdmin

---

Happy monitoring! 🇹🇭🚗