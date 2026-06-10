import time
import numpy as np
from .vision import VisionSystem
from .storage import UserManager


import serial, time
esp32 = serial.Serial(port='/dev/ttyUSB0', baudrate=115200, timeout=0.1)
time.sleep(2)


class SecuritySystem:
    # States
    STATE_IDLE = "IDLE"
    STATE_REGISTER_NAME = "REGISTER_NAME"
    STATE_REGISTER_CAPTURE = "REGISTER_CAPTURE"
    STATE_ADD_GESTURE = "ADD_GESTURE"
    STATE_ACCESS_DENIED = "ACCESS_DENIED"
    STATE_VERIFIED = "VERIFIED"
    STATE_VERIFICATION_FAILED = "VERIFICATION_FAILED"
    STATE_LOCKED = "LOCKED"

    def __init__(self):
        self.vision = VisionSystem()
        self.user_manager = UserManager()
        
        self.state = self.STATE_IDLE
        self.attempts = 5 # Default max attempts
        self.max_attempts = 5
        self.message = "Initializing..."
        self.sub_message = ""
        
        # Timers
        self.timer_start = 0
        self.timer_start = 0
        self.lockout_duration = 15 # Updated to 15 seconds
        self.denied_duration = 1
        self.failure_duration = 3 # 3 seconds delay after failure
        self.warning_timer = 0
        
        # Registration vars
        self.reg_name = ""
        self.reg_frames = []
        self.reg_start_time = 0
        self.reg_duration = 5 # 5 seconds capture
        
        # Add Gesture vars
        self.gesture_user = None
        
        # Verification logic
        self.last_gesture = None
        self.same_gesture_count = 0

    def reset_attempts(self):
        self.attempts = self.max_attempts

    def handle_input(self, key):
        if self.state == self.STATE_LOCKED:
            return # Block input
            
        if key == 'r':
            self.state = self.STATE_REGISTER_NAME
            self.message = "Enter Name"
            self.sub_message = "Type name in popup"
            return "input_name" # UI trigger
            
        elif key == 'g':
            self.state = self.STATE_ADD_GESTURE
            self.message = "Add Gesture"
            self.sub_message = "Show your Face to identify"
            
        elif key == 'esc':
            return "quit"

    def start_registration_capture(self, name):
        if name in self.user_manager.users:
            self.message = "Error"
            self.sub_message = "User already registered"
            self.state = self.STATE_IDLE
            return
            
        self.reg_name = name
        self.state = self.STATE_REGISTER_CAPTURE
        self.reg_frames = []
        self.reg_start_time = time.time()
        self.message = "Registering..."
        self.sub_message = "Show Face AND Gesture"

    def update(self, frame):
        # State: LOCKED
        if self.state == self.STATE_LOCKED:
            remaining = int(self.lockout_duration - (time.time() - self.timer_start))
            self.message = "SYSTEM LOCKED"
            self.sub_message = f"Wait {remaining}s"
            if remaining <= 0:
                self.state = self.STATE_IDLE
                self.reset_attempts()
                self.message = "Ready"
            return frame

        # State: ACCESS DENIED (Transient)
        if self.state == self.STATE_ACCESS_DENIED:
            if time.time() - self.timer_start > self.denied_duration:
                self.state = self.STATE_LOCKED
                self.timer_start = time.time()
            return frame
            
        # State: VERIFIED (Transient)
        if self.state == self.STATE_VERIFIED:
             if time.time() - self.timer_start > 2.0:
                 self.state = self.STATE_IDLE
                 self.reset_attempts()
                 self.message = "Ready"
             return frame

        # State: VERIFICATION FAILED (Delay)
        if self.state == self.STATE_VERIFICATION_FAILED:
            elapsed = time.time() - self.timer_start
            remaining = int(self.failure_duration - elapsed) + 1 # +1 for display
            self.message = "VERIFICATION FAILED"
            self.sub_message = f"Change Gesture/Face... {remaining}s"
            
            if elapsed > self.failure_duration:
                 self.state = self.STATE_IDLE
                 self.message = "Ready"
                 self.sub_message = ""
            return frame
            
        # Get Known Encodings

        # Get Known Encodings
        encodings, names = self.user_manager.get_known_encodings()
        
        # Process Frame
        results = self.vision.process_frame(frame, encodings, names)
        
        # Logic based on State
        if self.state == self.STATE_REGISTER_CAPTURE:
            self._handle_registration(results)
        elif self.state == self.STATE_ADD_GESTURE:
            self._handle_add_gesture(results)
        elif self.state == self.STATE_IDLE:
            self._handle_verification(results)
            
        return frame

    def _handle_registration(self, results):
        elapsed = time.time() - self.reg_start_time
        remaining = int(self.reg_duration - elapsed)
        self.sub_message = f"Capturing... {remaining}s"
        
        # Must have face and gesture
        if results["face_detected"] and results["hand_detected"]:
            if results["face_encoding"] is not None:
                self.reg_frames.append({
                    "encoding": results["face_encoding"],
                    "gesture": results["gesture"]
                })
        else:
             self.sub_message = "Show Face AND Gesture!"
             
        if elapsed > self.reg_duration:
            # Finish registration
            if len(self.reg_frames) > 5: # Threshold
                # Average encoding? Or just take best/last? taking last for now
                final_enc = self.reg_frames[-1]["encoding"]
                final_gest = self.reg_frames[-1]["gesture"]
                
                success = self.user_manager.register_user(self.reg_name, final_enc, final_gest)
                if success:
                    self.message = "Registered!"
                    self.sub_message = f"User {self.reg_name} added."
                    self.reset_attempts()
                else:
                    self.message = "Failed"
                    self.sub_message = "User already exists?"
            else:
                self.message = "Failed"
                self.sub_message = "Not enough data captured"
                
            self.state = self.STATE_IDLE
            self.timer_start = time.time() # Delay slightly?

    def _handle_add_gesture(self, results):
        # 1. Identify User
        if not self.gesture_user:
            self.message = "Identify Yourself"
            if results["face_name"] and results["face_name"] != "Unknown":
                self.gesture_user = results["face_name"]
                self.message = f"Hello {self.gesture_user}"
                self.sub_message = "Show NEW Gesture to add"
                self.reg_start_time = time.time() # Reuse timer for capture duration
            elif results["face_name"] == "Unknown":
                self.sub_message = "User not registered"
        else:
            # 2. Capture new gesture
            elapsed = time.time() - self.reg_start_time
            remaining = int(self.reg_duration - elapsed)
            self.sub_message = f"Hold Gesture... {remaining}s"
            
            if results["hand_detected"]:
                current_gesture = results["gesture"]
                # Save it
                if elapsed > self.reg_duration:
                    self.user_manager.add_gesture(self.gesture_user, current_gesture)
                    self.message = "Gesture Added"
                    self.sub_message = f"Added {current_gesture}"
                    self.reset_attempts() # Reset attempts after gesture add
                    self.state = self.STATE_IDLE
                    self.gesture_user = None

    def _handle_verification(self, results):
        face = results["face_name"]
        gesture = results["gesture"]
        
        # Update Liveness
        if results["blink"]:
            self.warning_timer = time.time() # Hijacking this for liveness timestamp or use new variable
            # We can use a separate variable for cleaner logic
            # Let's assume liveness is valid for 2 seconds after a blink
            pass

        # Check Liveness validity (Simple approach: if blink detected in last 3 seconds)
        is_live = False
        if results["blink"]:
             self.last_blink_time = time.time()
             is_live = True
        elif hasattr(self, 'last_blink_time') and time.time() - self.last_blink_time < 3.0:
             is_live = True

        # 1. Missing Input Logic
        if (results["face_detected"] and not results["hand_detected"]) or \
           (results["hand_detected"] and not results["face_detected"]):
            if self.warning_timer == 0:
                self.warning_timer = time.time()
            elif time.time() - self.warning_timer > 5.0:
                self.sub_message = "Show BOTH Face and Gesture"
            return # Do not decrease attempts yet
        else:
            self.warning_timer = 0 # Reset warning timer
            
        if not results["face_detected"] and not results["hand_detected"]:
            self.message = "Ready"
            if is_live:
                 self.sub_message = "Liveness Confirmed. Show Gesture."
            else:
                 self.sub_message = "Blink, then Show Face + Gesture"
            return

        # 2. Both Present Logic
        if face and face != "Unknown":
            # Check user gestures
            user_gestures = self.user_manager.get_user_gestures(face)
            if gesture in user_gestures:
                if is_live:
                    # ACCESS GRANTED
                    self.state = self.STATE_VERIFIED
                    self.message = "ACCESS GRANTED"
                    esp32.write(b'G')
                    self.sub_message = f"Welcome {face}"
                    self.timer_start = time.time()
                    self.user_manager.update_last_verified(face)
                    self.reset_attempts()
                    return
                else:
                    self.message = "LIVENESS CHECK"
                    self.sub_message = "Please Blink Your Eyes"
                    return # Wait for blink
            else:
                # Wrong Gesture
                pass # Fall through to failure
        else:
            # Wrong Face or Unknown
            pass

        # FAILURE CASE
        # Check if gesture changed to avoid rapid decrease
        if gesture != self.last_gesture:
             self.attempts -= 1
             self.last_gesture = gesture
             
             # Trigger Failure Delay
             self.state = self.STATE_VERIFICATION_FAILED
             self.timer_start = time.time()
             
        self.message = "VERIFICATION FAILED"
        if not is_live:
            self.sub_message = "Blink Required"
        else:
            self.sub_message = f"Attempts: {self.attempts}"
        
        if self.attempts <= 0:
            self.state = self.STATE_ACCESS_DENIED
            self.message = "ACCESS DENIED"
            esp32.write(b'D')
            self.sub_message = "Locked out"
            self.timer_start = time.time()
