# EYES Backend

Python FastAPI backend for gesture control.

## Setup
```bash
pip install -r requirements.txt
python main.py
```

## Endpoints
- `GET /` - Health check
- `GET /cameras` - List available cameras
- `WS /ws/gestures` - Real-time gesture stream
