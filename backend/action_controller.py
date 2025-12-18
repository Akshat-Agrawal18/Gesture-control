"""
EYES Action Controller
Executes desktop actions based on detected gestures.
Controls: Desktop switching, volume, brightness.
"""

import pyautogui
import screen_brightness_control as sbc
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL, CoInitialize
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from typing import Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class ActionType(Enum):
    DESKTOP_NEXT = "desktop_next"
    DESKTOP_PREV = "desktop_prev"
    DESKTOP_NEW = "desktop_new"
    VOLUME_SET = "volume_set"
    BRIGHTNESS_SET = "brightness_set"


@dataclass
class ActionConfig:
    """Configuration for which actions are enabled"""
    desktop_control: bool = True
    volume_control: bool = True
    brightness_control: bool = True


class ActionController:
    """
    Executes desktop actions based on gesture detection.
    Thread-safe and configurable.
    """
    
    def __init__(self, config: Optional[ActionConfig] = None):
        self.config = config or ActionConfig()
        
        # PyAutoGUI config
        pyautogui.PAUSE = 0.01
        pyautogui.FAILSAFE = True
        
        # Initialize audio (Windows)
        self._volume = None
        self._init_audio()
        
        # Current levels
        self.current_volume = 50
        self.current_brightness = 50
    
    def _init_audio(self):
        """Initialize Windows audio control"""
        try:
            CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._volume = cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            print(f"Audio init warning: {e}")
            self._volume = None
    
    def update_config(self, config: ActionConfig):
        """Update action configuration"""
        self.config = config
    
    # ==================== DESKTOP CONTROL ====================
    
    def next_desktop(self) -> bool:
        """Switch to next virtual desktop"""
        if not self.config.desktop_control:
            return False
        
        try:
            pyautogui.hotkey('win', 'ctrl', 'right')
            return True
        except Exception as e:
            print(f"Desktop switch error: {e}")
            return False
    
    def prev_desktop(self) -> bool:
        """Switch to previous virtual desktop"""
        if not self.config.desktop_control:
            return False
        
        try:
            pyautogui.hotkey('win', 'ctrl', 'left')
            return True
        except Exception as e:
            print(f"Desktop switch error: {e}")
            return False
    
    def new_desktop(self) -> bool:
        """Create a new virtual desktop"""
        if not self.config.desktop_control:
            return False
        
        try:
            pyautogui.hotkey('win', 'ctrl', 'd')
            return True
        except Exception as e:
            print(f"New desktop error: {e}")
            return False
    
    # ==================== VOLUME CONTROL ====================
    
    def set_volume(self, level: int) -> bool:
        """Set system volume (0-100)"""
        if not self.config.volume_control or not self._volume:
            return False
        
        try:
            level = max(0, min(100, level))  # Clamp to 0-100
            vol_range = self._volume.GetVolumeRange()
            min_vol, max_vol = vol_range[0], vol_range[1]
            
            # Map 0-100 to volume range
            vol = np.interp(level, [0, 100], [min_vol, max_vol])
            self._volume.SetMasterVolumeLevel(vol, None)
            self.current_volume = level
            return True
        except Exception as e:
            print(f"Volume error: {e}")
            return False
    
    def adjust_volume_by_pinch(self, pinch_distance: float, min_dist: float = 30, max_dist: float = 200) -> int:
        """Adjust volume based on pinch distance"""
        level = int(np.interp(pinch_distance, [min_dist, max_dist], [0, 100]))
        self.set_volume(level)
        return level
    
    def get_volume(self) -> int:
        """Get current volume level"""
        if self._volume:
            try:
                vol_range = self._volume.GetVolumeRange()
                current = self._volume.GetMasterVolumeLevel()
                return int(np.interp(current, [vol_range[0], vol_range[1]], [0, 100]))
            except:
                pass
        return self.current_volume
    
    # ==================== BRIGHTNESS CONTROL ====================
    
    def set_brightness(self, level: int) -> bool:
        """Set screen brightness (0-100)"""
        if not self.config.brightness_control:
            return False
        
        try:
            level = max(0, min(100, level))  # Clamp to 0-100
            sbc.set_brightness(level)
            self.current_brightness = level
            return True
        except Exception as e:
            print(f"Brightness error: {e}")
            return False
    
    def adjust_brightness_by_pinch(self, pinch_distance: float, min_dist: float = 30, max_dist: float = 200) -> int:
        """Adjust brightness based on pinch distance"""
        level = int(np.interp(pinch_distance, [min_dist, max_dist], [0, 100]))
        self.set_brightness(level)
        return level
    
    def get_brightness(self) -> int:
        """Get current brightness level"""
        try:
            levels = sbc.get_brightness()
            if levels:
                return levels[0] if isinstance(levels, list) else levels
        except:
            pass
        return self.current_brightness
