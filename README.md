
## 🐳 Docker Compose (Production + CCTV)

Run production backend + dashboard

```shell
docker compose up -d alpr-backend alpr-frontend
```

Open:

- Backend API: `http://localhost:8080/latest`
- Frontend dashboard: `http://localhost:8501`

GPU production mode (RTX 3060 and other NVIDIA GPUs):

```shell
CCTV_SOURCE="rtsp://user:password@camera-ip:554/stream1" docker compose up -d alpr-backend-gpu alpr-frontend-gpu
```

Runtime artifacts are persisted to `./artifacts`:

- `latest_report.json` (latest ALPR result)
- `latest_frame.jpg` (latest annotated frame)
- `events.jsonl` (stream of detection events)

Useful environment variables:

- `FRAME_STRIDE` (default: `5`) — run ALPR every N frames
- `RECONNECT_WAIT_SECONDS` (default: `2`) — reconnect delay when stream drops

> [!NOTE]
> GPU mode requires NVIDIA Container Toolkit and Docker Compose support for `gpus: all`.
