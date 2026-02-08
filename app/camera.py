import cv2
import threading
import time

class CameraManager:
    def __init__(self, source=0):
        self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW) # CAP_DSHOW for faster startup on Windows
        if not self.cap.isOpened():
             self.cap = cv2.VideoCapture(source)
        
        self.lock = threading.Lock()
        self.frame = None
        self.running = False
        self.thread = None

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(0.01)

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.cap.release()
