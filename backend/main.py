"""
EYES Backend - FastAPI Server
Main entry point for the gesture control backend.
Provides WebSocket API for real-time gesture streaming.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import base64
import cv2
from typing import Dict, List, Optional
from dataclasses import asdict
from contextlib import asynccontextmanager
import threading
import time

from gesture_engine import GestureEngine, GestureConfig, GestureType
from camera_manager import CameraManager, list_all_cameras, CameraInfo
from action_controller import ActionController, ActionConfig
from supabase_client import SupabaseManager
from sheets_client import SheetsManager

# ==================== APP STATE ====================

class AppState:
    """Global application state"""
    def __init__(self):
        self.camera_manager = CameraManager()
        self.gesture_engine = GestureEngine()
        self.action_controller = ActionController()
        
        # Cloud Clients
        self.supabase = SupabaseManager()
        self.sheets = SheetsManager()
        
        self.is_running = False
        self._process_thread: Optional[threading.Thread] = None
        self.connected_clients: List[WebSocket] = []
        
        # Settings
        self.settings = {
            "desktop_control": True,
            "volume_control": True,
            "brightness_control": True,
            "swipe_sensitivity": 100,
            "cooldown": 0.75,
            "selected_camera": "0"
        }
        
        # Recent gestures log
        self.gesture_log: List[dict] = []
        self.max_log_size = 50


state = AppState()


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("🚀 EYES Backend starting...")
    yield
    print("👋 EYES Backend shutting down...")
    stop_gesture_detection()
    state.camera_manager.cleanup()


# ==================== APP SETUP ====================

app = FastAPI(
    title="EYES Gesture Control",
    description="Backend API for gesture-based desktop control",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== HELPER FUNCTIONS ====================

def gesture_callback(result):
    """Called when a gesture is detected"""
    if result.gesture == GestureType.NONE:
        return
    
    # Prepare Log Entry
    log_entry = {
        "gesture": result.gesture.value,
        "hand": result.hand_label,
        "confidence": round(result.confidence, 2),
        "timestamp": time.time(),
        "volume_at_time": state.action_controller.get_volume(),
        "brightness_at_time": state.action_controller.get_brightness()
    }
    
    # 1. Update In-Memory Log
    state.gesture_log.insert(0, log_entry)
    if len(state.gesture_log) > state.max_log_size:
        state.gesture_log.pop()
        
    # 2. Log to Cloud (Fire and Forget)
    # We do this in a thread to not block the vision loop
    threading.Thread(target=lambda: state.supabase.log_gesture(log_entry)).start()
    threading.Thread(target=lambda: state.sheets.log_session_data(log_entry)).start()
    
    # Execute action based on gesture
    if result.gesture == GestureType.SWIPE_LEFT:
        state.action_controller.next_desktop()
    elif result.gesture == GestureType.SWIPE_RIGHT:
        state.action_controller.prev_desktop()
    elif result.gesture == GestureType.SWIPE_UP:
        state.action_controller.new_desktop()
    elif result.gesture == GestureType.PINCH:
        # Pinch controls based on hand
        if result.hand_label == "Left":
            state.action_controller.adjust_volume_by_pinch(result.pinch_distance)
        else:
            state.action_controller.adjust_brightness_by_pinch(result.pinch_distance)


def start_gesture_detection():
    """Start the gesture detection loop"""
    if state.is_running:
        return
    
    # Connect to camera
    source = state.settings.get("selected_camera", "0")
    if not state.camera_manager.connect(source):
        raise Exception(f"Failed to connect to camera: {source}")
    
    # Set gesture callback
    state.gesture_engine.on_gesture = gesture_callback
    
    # Update configs
    state.gesture_engine.update_config(GestureConfig(
        swipe_threshold=state.settings.get("swipe_sensitivity", 100),
        cooldown=state.settings.get("cooldown", 0.75)
    ))
    state.action_controller.update_config(ActionConfig(
        desktop_control=state.settings.get("desktop_control", True),
        volume_control=state.settings.get("volume_control", True),
        brightness_control=state.settings.get("brightness_control", True)
    ))
    
    state.is_running = True
    
    def process_loop():
        while state.is_running:
            frame = state.camera_manager.read_frame()
            if frame is not None:
                processed_frame, gestures = state.gesture_engine.process_frame(frame)
                
                # Broadcast to connected WebSocket clients
                if state.connected_clients:
                    try:
                        # Encode frame as base64 JPEG
                        _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                        frame_b64 = base64.b64encode(buffer).decode('utf-8')
                        
                        message = {
                            "type": "frame",
                            "frame": frame_b64,
                            "fps": round(state.gesture_engine.get_fps(), 1),
                            "gestures": [
                                {"gesture": g.gesture.value, "hand": g.hand_label, "confidence": g.confidence}
                                for g in gestures if g.gesture != GestureType.NONE
                            ],
                            "volume": state.action_controller.get_volume(),
                            "brightness": state.action_controller.get_brightness()
                        }
                        
                        # Send to all clients (done in async context below)
                        asyncio.run(broadcast_message(message))
                    except Exception as e:
                        print(f"Broadcast error: {e}")
            
            time.sleep(0.016)  # ~60 FPS cap
    
    state._process_thread = threading.Thread(target=process_loop, daemon=True)
    state._process_thread.start()


def stop_gesture_detection():
    """Stop the gesture detection loop"""
    state.is_running = False
    if state._process_thread:
        state._process_thread.join(timeout=2.0)
        state._process_thread = None
    state.camera_manager.disconnect()


async def broadcast_message(message: dict):
    """Broadcast a message to all connected WebSocket clients"""
    dead_clients = []
    for client in state.connected_clients:
        try:
            await client.send_json(message)
        except:
            dead_clients.append(client)
    
    for client in dead_clients:
        state.connected_clients.remove(client)


# ==================== REST ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "name": "EYES Gesture Control Backend",
        "version": "1.0.0",
        "is_running": state.is_running
    }


@app.get("/cameras")
async def get_cameras():
    """List all available cameras"""
    cameras = list_all_cameras()
    return {
        "cameras": [
            {"id": cam.id, "name": cam.name, "type": cam.type.value, "source": cam.source}
            for cam in cameras
        ]
    }


@app.post("/cameras/test")
async def test_camera(url: str):
    """Test an IP camera URL"""
    is_available = state.camera_manager.test_ip_camera(url)
    return {"url": url, "available": is_available}


@app.get("/settings")
async def get_settings():
    """Get current settings"""
    return state.settings


@app.post("/settings")
async def update_settings(settings: dict):
    """Update settings"""
    # Check if camera is changing
    new_camera = settings.get("selected_camera")
    old_camera = state.settings.get("selected_camera")
    camera_changed = new_camera is not None and new_camera != old_camera
    
    state.settings.update(settings)
    
    # Apply settings if running
    if state.is_running:
        # If camera changed, we need to restart the detection loop
        if camera_changed:
            print(f"Camera changed from {old_camera} to {new_camera}. Restarting system...")
            stop_gesture_detection()
            # Small delay to ensure resources are freed
            time.sleep(0.5)
            start_gesture_detection()
        else:
            # Just update configs without restart
            state.gesture_engine.update_config(GestureConfig(
                swipe_threshold=state.settings.get("swipe_sensitivity", 100),
                cooldown=state.settings.get("cooldown", 0.75)
            ))
            state.action_controller.update_config(ActionConfig(
                desktop_control=state.settings.get("desktop_control", True),
                volume_control=state.settings.get("volume_control", True),
                brightness_control=state.settings.get("brightness_control", True)
            ))
    
    return {"status": "updated", "settings": state.settings}


@app.post("/start")
async def start_detection():
    """Start gesture detection"""
    try:
        start_gesture_detection()
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop")
async def stop_detection():
    """Stop gesture detection"""
    stop_gesture_detection()
    return {"status": "stopped"}


@app.get("/status")
async def get_status():
    """Get current system status"""
    return {
        "is_running": state.is_running,
        "camera": state.settings.get("selected_camera"),
        "fps": state.gesture_engine.get_fps() if state.is_running else 0,
        "volume": state.action_controller.get_volume(),
        "brightness": state.action_controller.get_brightness(),
        "connected_clients": len(state.connected_clients)
    }


@app.get("/gestures/log")
async def get_gesture_log():
    """Get recent gesture history"""
    return {"log": state.gesture_log}


# ==================== WEBSOCKET ====================

@app.websocket("/ws/gestures")
async def websocket_gestures(websocket: WebSocket):
    """WebSocket endpoint for real-time gesture streaming"""
    await websocket.accept()
    state.connected_clients.append(websocket)
    
    try:
        while True:
            # Handle incoming messages (settings updates, commands)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                
                if data.get("type") == "settings":
                    state.settings.update(data.get("settings", {}))
                elif data.get("type") == "start":
                    start_gesture_detection()
                elif data.get("type") == "stop":
                    stop_gesture_detection()
                    
            except asyncio.TimeoutError:
                pass  # No message, continue
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in state.connected_clients:
            state.connected_clients.remove(websocket)


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    print("🖐️ EYES Gesture Control Backend")
    print("=" * 40)
    print("Starting server at http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 40)
    uvicorn.run(app, host="0.0.0.0", port=8000)
