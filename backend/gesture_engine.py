"""
EYES Gesture Engine
Unified gesture detection using MediaPipe for hand tracking.
Supports desktop control, volume, and brightness gestures.
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math
from dataclasses import dataclass
from typing import Callable, Optional, List, Dict, Any
from enum import Enum


class GestureType(Enum):
    NONE = "none"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    PINCH = "pinch"
    GRAB = "grab"
    OPEN_PALM = "open_palm"
    THUMBS_UP = "thumbs_up"
    PEACE = "peace"


@dataclass
class GestureResult:
    """Result from gesture detection"""
    gesture: GestureType
    confidence: float
    hand_label: str  # "Left" or "Right"
    landmarks: List[Dict[str, float]]
    pinch_distance: float = 0.0
    timestamp: float = 0.0


@dataclass
class GestureConfig:
    """Configuration for gesture detection"""
    swipe_threshold: int = 100
    time_window: float = 0.3
    cooldown: float = 0.75
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.7
    max_hands: int = 2


class GestureEngine:
    """
    Unified gesture detection engine using MediaPipe.
    Detects swipes, pinches, and custom hand gestures.
    """
    
    def __init__(self, config: Optional[GestureConfig] = None):
        self.config = config or GestureConfig()
        
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            model_complexity=1,
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
            max_num_hands=self.config.max_hands
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Tracking state
        self.history_x: List[float] = []
        self.history_y: List[float] = []
        self.history_time: List[float] = []
        self.last_trigger_time: float = 0
        
        # Callbacks
        self.on_gesture: Optional[Callable[[GestureResult], None]] = None
        
        # Stats
        self.fps = 0
        self.last_frame_time = time.time()
        
    def update_config(self, config: GestureConfig):
        """Update gesture configuration dynamically"""
        self.config = config
        # Recreate hands with new config
        self.hands = self.mp_hands.Hands(
            model_complexity=1,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
            max_num_hands=config.max_hands
        )
    
    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, List[GestureResult]]:
        """
        Process a single frame and detect gestures.
        Returns: (annotated_frame, list_of_gestures)
        """
        # Calculate FPS
        current_time = time.time()
        if current_time - self.last_frame_time > 0:
            self.fps = 1 / (current_time - self.last_frame_time)
        self.last_frame_time = current_time
        
        # Flip and convert
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.hands.process(rgb_frame)
        gestures: List[GestureResult] = []
        
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, 
                results.multi_handedness
            ):
                # Draw landmarks
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
                
                # Get hand label
                hand_label = handedness.classification[0].label
                
                # Extract landmark positions
                landmarks = []
                for lm in hand_landmarks.landmark:
                    landmarks.append({
                        "x": lm.x,
                        "y": lm.y,
                        "z": lm.z
                    })
                
                # Detect gestures
                gesture_result = self._detect_gestures(
                    hand_landmarks, hand_label, landmarks, w, h, current_time
                )
                
                if gesture_result:
                    gestures.append(gesture_result)
                    
                    # Trigger callback
                    if self.on_gesture and gesture_result.gesture != GestureType.NONE:
                        self.on_gesture(gesture_result)
        
        # Draw FPS
        cv2.putText(
            frame, f"FPS: {int(self.fps)}", 
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, (0, 255, 0), 2
        )
        
        return frame, gestures
    
    def _detect_gestures(
        self, 
        hand_landmarks, 
        hand_label: str, 
        landmarks: List[Dict], 
        w: int, 
        h: int,
        current_time: float
    ) -> Optional[GestureResult]:
        """Detect various gestures from hand landmarks"""
        
        # Get key points
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        palm_center = hand_landmarks.landmark[9]
        
        # Calculate pinch distance (thumb to index)
        pinch_dist = math.hypot(
            (thumb_tip.x - index_tip.x) * w,
            (thumb_tip.y - index_tip.y) * h
        )
        
        # Track palm center for swipes
        cx = int(palm_center.x * w)
        cy = int(palm_center.y * h)
        
        self.history_x.append(cx)
        self.history_y.append(cy)
        self.history_time.append(current_time)
        
        # Prune old history
        while self.history_time and current_time - self.history_time[0] > self.config.time_window:
            self.history_x.pop(0)
            self.history_y.pop(0)
            self.history_time.pop(0)
        
        detected_gesture = GestureType.NONE
        confidence = 0.0
        
        # Check cooldown
        if current_time - self.last_trigger_time > self.config.cooldown:
            
            # Detect swipes
            if len(self.history_x) >= 2:
                dx = self.history_x[-1] - self.history_x[0]
                dy = self.history_y[-1] - self.history_y[0]
                
                # Debug print for movement
                # if abs(dx) > 20 or abs(dy) > 20:
                #     print(f"Tracking: dx={dx}, dy={dy}")

                if abs(dx) > abs(dy):  # Horizontal
                    if dx > self.config.swipe_threshold:
                        detected_gesture = GestureType.SWIPE_RIGHT
                        confidence = min(abs(dx) / 100, 1.0)
                        self._clear_history()
                        print(">>> SWIPE RIGHT DETECTED")
                    elif dx < -self.config.swipe_threshold:
                        detected_gesture = GestureType.SWIPE_LEFT
                        confidence = min(abs(dx) / 100, 1.0)
                        self._clear_history()
                        print(">>> SWIPE LEFT DETECTED")
                else:  # Vertical
                    if dy < -self.config.swipe_threshold:
                        detected_gesture = GestureType.SWIPE_UP
                        confidence = min(abs(dy) / 100, 1.0)
                        self._clear_history()
                        print(">>> SWIPE UP DETECTED")
                    elif dy > self.config.swipe_threshold:
                        detected_gesture = GestureType.SWIPE_DOWN
                        confidence = min(abs(dy) / 100, 1.0)
                        self._clear_history()
                        print(">>> SWIPE DOWN DETECTED")
            
            # Detect Pinch / Control Mode
            # Only check for PINCH if no SWIPE was detected
            if detected_gesture == GestureType.NONE:
                # Allow a larger range (up to 250px) to enable slider control
                if pinch_dist < 250:
                    detected_gesture = GestureType.PINCH
                    confidence = 1.0
            
            if detected_gesture != GestureType.NONE:
                # Only debounce SWIPES, not continuous pinch
                if "swipe" in detected_gesture.value:
                    self.last_trigger_time = current_time
        
        return GestureResult(
            gesture=detected_gesture,
            confidence=confidence,
            hand_label=hand_label,
            landmarks=landmarks,
            pinch_distance=pinch_dist,
            timestamp=current_time
        )
    
    def _clear_history(self):
        """Clear swipe tracking history"""
        self.history_x = []
        self.history_y = []
        self.history_time = []
    
    def get_fps(self) -> float:
        """Get current FPS"""
        return self.fps
    
    def cleanup(self):
        """Release resources"""
        self.hands.close()
