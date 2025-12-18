import cv2
import time
import math
import mediapipe as mp
import numpy as np
import screen_brightness_control as sbc
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL, CoInitialize
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from google.protobuf.json_format import MessageToDict

# --- 1. SETUP ---
cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

# --- 2. FAIL-SAFE AUDIO SETUP ---
CoInitialize() 
try:
    # Method A: Standard
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
except:
    try:
        # Method B: Backup (Specific for your PC)
        enum = AudioUtilities.GetDeviceEnumerator()
        device = enum.GetDefaultAudioEndpoint(0, 1)
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    except:
        print("Audio Error. Could not connect to speakers.")
        exit()

volume = cast(interface, POINTER(IAudioEndpointVolume))
volRange = volume.GetVolumeRange()
minVol = volRange[0]
maxVol = volRange[1]

# --- 3. VARIABLES ---
volBar, volPer = 400, 0
brightBar, brightPer = 400, 0
pTime = 0  # <--- I ADDED THIS LINE TO FIX THE ERROR

print("System Ready! Left Hand = Volume | Right Hand = Brightness")

while True:
    success, img = cap.read()
    if not success:
        break

    img = cv2.flip(img, 1) 
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    if results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Get Label
            label = MessageToDict(handedness)['classification'][0]['label']
            
            lmList = []
            for id, lm in enumerate(hand_landmarks.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])

            if lmList:
                x1, y1 = lmList[4][1], lmList[4][2]
                x2, y2 = lmList[8][1], lmList[8][2]
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

                length = math.hypot(x2 - x1, y2 - y1)

                # --- CONTROLS ---
                if label == "Left": 
                    vol = np.interp(length, [30, 200], [minVol, maxVol])
                    volBar = np.interp(length, [30, 200], [400, 150])
                    volPer = np.interp(length, [30, 200], [0, 100])
                    volume.SetMasterVolumeLevel(vol, None)
                    cv2.putText(img, "Vol", (cx-20, cy-20), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

                elif label == "Right":
                    bright = np.interp(length, [30, 200], [0, 100])
                    brightBar = np.interp(length, [30, 200], [400, 150])
                    brightPer = np.interp(length, [30, 200], [0, 100])
                    try:
                        sbc.set_brightness(int(bright))
                    except:
                        pass 
                    cv2.putText(img, "Bright", (cx-30, cy-20), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)

    # DRAW BARS
    cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 3)
    cv2.rectangle(img, (50, int(volBar)), (85, 400), (0, 255, 0), cv2.FILLED)
    cv2.putText(img, f'{int(volPer)}%', (40, 450), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 3)
    cv2.putText(img, 'VOL', (40, 140), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 3)

    h, w, c = img.shape
    cv2.rectangle(img, (w-85, 150), (w-50, 400), (0, 255, 255), 3)
    cv2.rectangle(img, (w-85, int(brightBar)), (w-50, 400), (0, 255, 255), cv2.FILLED)
    cv2.putText(img, f'{int(brightPer)}%', (w-95, 450), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 3)
    cv2.putText(img, 'LIT', (w-95, 140), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 3)

    # FPS CALCULATION
    cTime = time.time()
    if (cTime - pTime) > 0: # Avoid division by zero
        fps = 1 / (cTime - pTime)
    else:
        fps = 0
    pTime = cTime
    
    cv2.putText(img, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 3)

    cv2.imshow("Sci-Fi Controller Fixed", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()