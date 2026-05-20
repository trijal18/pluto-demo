import cv2
import mediapipe as mp
import numpy as np
import sys
import os
from PyQt6.QtCore import QThread, pyqtSignal

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.filters import LowPassFilter
from utils.gestures import HandChassis

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class Point:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

class Category:
    def __init__(self, name, score, index):
        self.category_name, self.score, self.index = name, score, index

class VisionWorker(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    landmarks_signal = pyqtSignal(list, list) # landmarks, handedness

    def __init__(self, model_path="hand_landmarker.task"):
        super().__init__()
        self._run_flag = True
        self.model_path = model_path
        
        # Ensure model path is absolute or correctly relative to 'new/'
        if not os.path.isabs(self.model_path):
            # new/gcs/workers/vision_worker.py -> new/
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.model_path = os.path.join(base_dir, self.model_path)

    def run(self):
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        cap = cv2.VideoCapture(0)
        
        with vision.HandLandmarker.create_from_options(options) as landmarker:
            while self._run_flag:
                success, frame = cap.read()
                if success:
                    # Process frame
                    frame = cv2.flip(frame, 1)
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
                    
                    result = landmarker.detect(mp_image)
                    
                    # 1. Emit Image Signal
                    self.change_pixmap_signal.emit(frame)
                    
                    # 2. Serialize and Emit Landmarks Signal
                    if result.hand_landmarks:
                        s_landmarks = []
                        for hand in result.hand_landmarks:
                            s_landmarks.append([Point(lm.x, lm.y, lm.z) for lm in hand])
                        
                        s_handedness = []
                        for hand_info in result.handedness:
                            # hand_info is a list of Category objects
                            s_handedness.append([Category(h.category_name, h.score, h.index) for h in hand_info])
                        
                        self.landmarks_signal.emit(s_landmarks, s_handedness)
                    else:
                        self.landmarks_signal.emit([], [])
                
                self.msleep(10)
        
        cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.wait()
