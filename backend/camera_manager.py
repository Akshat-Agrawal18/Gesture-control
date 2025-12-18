"""
EYES Camera Manager
Handles multiple camera sources: USB webcams, phone cameras (DroidCam/IP Webcam), IP streams.
"""

import cv2
import threading
import time
from dataclasses import dataclass
from typing import Optional, List, Callable
from enum import Enum
import numpy as np


class CameraType(Enum):
    USB = "usb"
    IP_STREAM = "ip_stream"
    PHONE = "phone"


@dataclass
class CameraInfo:
    """Information about a camera source"""
    id: str
    name: str
    type: CameraType
    source: str  # Index for USB, URL for IP
    is_available: bool = True


class CameraManager:
    """
    Manages multiple camera sources with hot-swap support.
    Supports USB cameras, phone cameras via DroidCam/IP Webcam, and IP streams.
    """
    
    # Known phone camera patterns
    PHONE_PATTERNS = [
        ("http://{ip}:4747/video", "DroidCam"),
        ("http://{ip}:8080/video", "IP Webcam"),
        ("http://{ip}:4747/mjpegfeed", "DroidCam MJPEG"),
    ]
    
    def __init__(self):
        self.current_camera: Optional[cv2.VideoCapture] = None
        self.current_source: Optional[str] = None
        self.is_running = False
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._capture_thread: Optional[threading.Thread] = None
        
    def detect_usb_cameras(self) -> List[CameraInfo]:
        """Detect all available USB cameras"""
        cameras = []
        
        # Check up to 10 camera indices
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Use DirectShow on Windows
            if cap.isOpened():
                # Try to read a frame to confirm it works
                ret, _ = cap.read()
                if ret:
                    cameras.append(CameraInfo(
                        id=f"usb_{i}",
                        name=f"Camera {i}" if i > 0 else "Built-in Webcam",
                        type=CameraType.USB,
                        source=str(i),
                        is_available=True
                    ))
                cap.release()
        
        return cameras
    
    def test_ip_camera(self, url: str, timeout: float = 3.0) -> bool:
        """Test if an IP camera URL is accessible"""
        try:
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout * 1000))
            
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                return ret
            return False
        except:
            return False
    
    def get_phone_camera_url(self, ip: str, app: str = "droidcam") -> str:
        """Get the URL for a phone camera app"""
        patterns = {
            "droidcam": f"http://{ip}:4747/video",
            "ipwebcam": f"http://{ip}:8080/video",
            "iriun": f"http://{ip}:4747/video",
        }
        return patterns.get(app.lower(), f"http://{ip}:4747/video")
    
    def connect(self, source: str) -> bool:
        """
        Connect to a camera source.
        source can be: USB index (0, 1, 2...) or URL for IP camera
        """
        self.disconnect()
        
        try:
            # Check if it's a USB index
            if source.isdigit():
                self.current_camera = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
            else:
                # IP camera URL
                self.current_camera = cv2.VideoCapture(source)
            
            if self.current_camera.isOpened():
                # Configure camera
                self.current_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.current_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.current_camera.set(cv2.CAP_PROP_FPS, 30)
                
                self.current_source = source
                return True
            else:
                self.current_camera = None
                return False
                
        except Exception as e:
            print(f"Camera connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect current camera"""
        self.stop_capture()
        if self.current_camera:
            self.current_camera.release()
            self.current_camera = None
            self.current_source = None
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Read a single frame from the current camera"""
        if self.current_camera and self.current_camera.isOpened():
            ret, frame = self.current_camera.read()
            if ret:
                return frame
        return None
    
    def start_capture(self, on_frame: Optional[Callable[[np.ndarray], None]] = None):
        """Start continuous frame capture in a background thread"""
        if self.is_running:
            return
        
        self.is_running = True
        
        def capture_loop():
            while self.is_running and self.current_camera:
                frame = self.read_frame()
                if frame is not None:
                    with self._lock:
                        self._frame = frame
                    if on_frame:
                        on_frame(frame)
                time.sleep(0.01)  # ~60fps max
        
        self._capture_thread = threading.Thread(target=capture_loop, daemon=True)
        self._capture_thread.start()
    
    def stop_capture(self):
        """Stop background capture"""
        self.is_running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest captured frame (thread-safe)"""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None
    
    def get_preview_base64(self, scale: float = 0.5) -> Optional[str]:
        """Get a base64 encoded JPEG preview of the current frame"""
        import base64
        
        frame = self.get_latest_frame()
        if frame is None:
            return None
        
        # Resize for preview
        h, w = frame.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        preview = cv2.resize(frame, (new_w, new_h))
        
        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return base64.b64encode(buffer).decode('utf-8')
    
    def cleanup(self):
        """Release all resources"""
        self.disconnect()


# Utility function for quick camera listing
def list_all_cameras() -> List[CameraInfo]:
    """Quick utility to list all available cameras"""
    manager = CameraManager()
    cameras = manager.detect_usb_cameras()
    manager.cleanup()
    return cameras
