import cv2
import mediapipe as mp
import face_recognition
import numpy as np
from collections import deque
import time

class VisionSystem:
    def __init__(self):
        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

        # MediaPipe Face Mesh for Liveness (Blink)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Blink State
        self.left_eye_indices = [362, 385, 387, 263, 373, 380]
        self.right_eye_indices = [33, 160, 158, 133, 153, 144]
        self.blink_detected = False
        self.ear_history = deque(maxlen=20)
        self.blink_cooldown = 0

        # Processing optimization
        self.process_this_frame = True

    def calculate_ear(self, landmarks, indices, w, h):
        # Euclidean distance
        coords = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in indices])
        # Vertical 1: (1, 5) -> indices 1 and 5 (in the list)
        v1 = np.linalg.norm(coords[1] - coords[5])
        v2 = np.linalg.norm(coords[2] - coords[4])
        # Horizontal
        h_dist = np.linalg.norm(coords[0] - coords[3])
        ear = (v1 + v2) / (2.0 * h_dist)
        return ear

    def detect_gesture(self, hand_landmarks, handedness):
        # Improved gesture logic with strict counting and handedness
        tips = [4, 8, 12, 16, 20]
        state = []
        
        # Check if hand is right or left for thumb logic
        # handedness is "Left" or "Right".
        # MediaPipe's "Left" means the person's left hand (if not mirrored).
        
        # Fingers: Index to Pinky
        for tip in tips[1:]:
            pip = tip - 2
            # Y-axis decreases upwards
            if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y:
                state.append(1) # Open
            else:
                state.append(0) # Closed
                
        # Thumb Logic
        # For Right Hand: Thumb is to the left of IP joint when open (smaller x) ? 
        # Actually easier: check x distance.
        # Right Hand Open: Thumb Tip x < Thumb IP x (assuming palm faces camera)
        # Left Hand Open: Thumb Tip x > Thumb IP x
        
        thumb_tip = hand_landmarks.landmark[4]
        thumb_ip = hand_landmarks.landmark[3]
        
        if handedness == "Right":
            if thumb_tip.x < thumb_ip.x:
                state.append(1)
            else:
                state.append(0)
        else: # Left
            if thumb_tip.x > thumb_ip.x:
                state.append(1)
            else:
                state.append(0)

        # Strict Gesture Definitions
        fingers_up = sum(state)
        
        gesture_name = "Unknown"
        
        if fingers_up == 0:
            gesture_name = "Fist"
        elif fingers_up == 5:
            gesture_name = "Open Palm"
        elif state == [1, 1, 0, 0, 0]: # Index + Middle (Victory)
            gesture_name = "Victory"
        elif state == [0, 1, 0, 0, 0]: # Index only (Pointing)
            gesture_name = "Pointing1"
        elif state == [0, 1, 1, 0, 0]:
            gesture_name = "pointing2"
        elif state == [0, 1, 1, 1, 0]:
            gesture_name = "pointing3"
        elif state == [0, 1, 1, 1, 1]:
            gesture_name = "pointing4"
            
        return f"{handedness} {gesture_name}"

    def process_frame(self, frame, known_face_encodings, known_face_names):
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape
        
        results = {
            "face_detected": False,
            "face_name": None,
            "face_encoding": None,
            "hand_detected": False,
            "gesture": None,
            "blink": False,
            "landmarks": None # for drawing
        }

        # 1. Hand Tracking
        hand_result = self.hands.process(rgb_frame)
        if hand_result.multi_hand_landmarks:
            results["hand_detected"] = True
            # Get first hand
            results["landmarks"] = hand_result.multi_hand_landmarks[0]
            
            # Get Handedness
            # Multi_handedness returns a list of classification objects
            if hand_result.multi_handedness:
                # Get the label (Left or Right)
                handedness_obj = hand_result.multi_handedness[0].classification[0]
                handedness_label = handedness_obj.label
                results["gesture"] = self.detect_gesture(results["landmarks"], handedness_label)
            else:
                # Fallback if somehow no handedness
                results["gesture"] = self.detect_gesture(results["landmarks"], "Right")

        # 2. Face Recognition (Computationally expensive, skip frames or downscale if needed)
        # Using face_recognition library
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        if face_locations:
            results["face_detected"] = True
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            if face_encodings:
                encoding = face_encodings[0]
                results["face_encoding"] = encoding
                matches = face_recognition.compare_faces(known_face_encodings, encoding)
                name = "Unknown"
                
                # Use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, encoding)
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                
                results["face_name"] = name

        # 3. Liveness (Blink) - Use MediaPipe Face Mesh
        mesh_results = self.face_mesh.process(rgb_frame)
        if mesh_results.multi_face_landmarks:
            face_landmarks = mesh_results.multi_face_landmarks[0].landmark
            left_ear = self.calculate_ear(face_landmarks, self.left_eye_indices, w, h)
            right_ear = self.calculate_ear(face_landmarks, self.right_eye_indices, w, h)
            avg_ear = (left_ear + right_ear) / 2.0
            
            # Blink logic
            if avg_ear < 0.25: # Eyes closed
                self.blink_cooldown = time.time()
                # Consider it a blink if it opens again soon? 
                # For now just detecting "eyes closed" as part of blink
                pass
            else:
                if time.time() - self.blink_cooldown < 0.5: # Opened recently
                     self.blink_detected = True
        
        if time.time() - self.blink_cooldown > 2.0:
            self.blink_detected = False # Reset if no blink for a while

        results["blink"] = self.blink_detected
        
        return results
