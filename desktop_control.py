import cv2
import mediapipe as mp
import pyautogui
import time

# --- SETUP ---
cap = cv2.VideoCapture(0)
cap.set(3, 640) # Width
cap.set(4, 480) # Height

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    model_complexity=1,           # 1=Better accuracy
    min_detection_confidence=0.8, # Increased: stricter detection
    min_tracking_confidence=0.8,  # Increased: less jitter
    max_num_hands=1
)
mp_draw = mp.solutions.drawing_utils

# --- OPTIMIZATION ---
pyautogui.PAUSE = 0.01 # Fast response
pyautogui.FAILSAFE = True 

# --- VARIABLES ---
history_x = []
history_y = []
history_time = []
SWIPE_THRESHOLD = 100  # Lower threshold = more sensitive/faster trigger
TIME_WINDOW = 0.3      # Shorter window = requires snappier swipes
COOLDOWN = 0.75        # Quicker reset
last_trigger_time = 0

print("System Ready!")
print("- Swipe UP (^): Create New Desktop")
print("- Swipe LEFT/RIGHT (<->): Switch Desktops")
print("- Move mouse to any corner to FORCE STOP")

while True:
    success, img = cap.read()
    if not success:
        break

    # Flip image for mirror effect
    img = cv2.flip(img, 1)
    h, w, c = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Track 'Middle Finger MCP' (Landmark 9) -> CENTER OF HAND
            # This is much more stable than a fingertip for whole-hand swipes
            cx = int(hand_landmarks.landmark[9].x * w)
            cy = int(hand_landmarks.landmark[9].y * h)
            
            # Draw Current Pos
            cv2.circle(img, (cx, cy), 15, (0, 0, 255), cv2.FILLED)

            current_time = time.time()
            history_x.append(cx)
            history_y.append(cy)
            history_time.append(current_time)

            # --- DRAW MOTION TRAIL ---
            # Visualizes the path "Snake" to help understand the gesture
            for i in range(1, len(history_x)):
                # Fade out color or thickness could be cool, but simple Green Line is clear
                pt1 = (history_x[i-1], history_y[i-1])
                pt2 = (history_x[i], history_y[i])
                cv2.line(img, pt1, pt2, (0, 255, 0), 4)
            # -------------------------

            # Keep history within time window
            while history_time and current_time - history_time[0] > TIME_WINDOW:
                history_x.pop(0)
                history_y.pop(0)
                history_time.pop(0)

            # Check for Swipe
            if len(history_x) >= 2:
                dx = history_x[-1] - history_x[0] 
                dy = history_y[-1] - history_y[0]
                
                # DEBUG INFO ON SCREEN
                cv2.putText(img, f"dx: {dx} dy: {dy}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                # Only trigger if cooldown passed
                if current_time - last_trigger_time > COOLDOWN:
                    
                    # Horizontal Swipes (Dominant X movement)
                    if abs(dx) > abs(dy):
                        # SWIPE RIGHT -> Previous Desktop
                        if dx > SWIPE_THRESHOLD: 
                            cv2.putText(img, "Previous Desktop", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                            print("Action: Previous Desktop")
                            pyautogui.hotkey('win', 'ctrl', 'left')
                            last_trigger_time = current_time
                            history_x = []
                            history_y = []
                            history_time = []
                        
                        # SWIPE LEFT -> Next Desktop (Fixed: Logical Left for User)
                        elif dx < -SWIPE_THRESHOLD:
                            cv2.putText(img, "Next Desktop", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                            print("Action: Next Desktop")
                            pyautogui.hotkey('win', 'ctrl', 'right')
                            last_trigger_time = current_time
                            history_x = []
                            history_y = []
                            history_time = []
                    
                    # Vertical Swipes (Dominant Y movement)
                    else:
                        # SWIPE UP -> Create New Desktop (Negative dy is UP in pixels)
                        if dy < -SWIPE_THRESHOLD:
                            cv2.putText(img, "New Desktop", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                            print("Action: Create New Desktop")
                            pyautogui.hotkey('win', 'ctrl', 'd')
                            last_trigger_time = current_time
                            history_x = []
                            history_y = []
                            history_time = []

    # Display Status
    img = cv2.flip(img, 0) # Unflip if needed? No, standard view.
    # Actually we don't need to flip 0.
    
    if time.time() - last_trigger_time < COOLDOWN:
        cv2.putText(img, "Cooldown...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    else:
        cv2.putText(img, "Ready", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Desktop Gesture Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
