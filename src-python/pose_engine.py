import cv2
import mediapipe as mp
import base64
import numpy as np
from typing import Dict, Any, Optional, Tuple

class PoseEngine:
    def __init__(self):
        # Initialize Mediapipe Pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize Mediapipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.cap = None

    def start_camera(self, device_id: int = 0) -> bool:
        """
        Initializes the OpenCV video capture.
        """
        self.cap = cv2.VideoCapture(device_id)
        return self.cap.isOpened()

    def stop_camera(self):
        """
        Releases the webcam.
        """
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.cap = None

    def capture_frame(self) -> Tuple[Optional[Dict[int, Dict[str, float]]], Optional[Dict[int, Dict[str, float]]], Optional[str], Optional[float], Optional[float], Optional[float]]:
        """
        Reads a frame from the webcam, mirrors it, encodes it as base64 JPEG,
        runs MediaPipe Pose & Face Mesh inference, computes ambient brightness, Eye Aspect Ratio,
        and pupil distance, and returns (pose_landmarks, world_landmarks, base64_frame, ear, avg_brightness, ipd_pixels).
        """
        if not self.cap or not self.cap.isOpened():
            return None, None, None, None, None, None

        ret, frame = self.cap.read()
        if not ret:
            return None, None, None, None, None, None

        # Mirror the frame horizontally (selfie style)
        frame = cv2.flip(frame, 1)

        # Compress to JPEG and encode to Base64
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
        except Exception:
            frame_base64 = None

        # Convert frame to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. Process Face Mesh for EAR (Eye Aspect Ratio) and IPD (depth estimation)
        face_results = self.face_mesh.process(rgb_frame)
        ear = None
        ipd_pixels = None
        if face_results.multi_face_landmarks:
            face_landmarks = face_results.multi_face_landmarks[0].landmark
            h_img, w_img, _ = frame.shape
            
            def get_pt(idx):
                lm = face_landmarks[idx]
                return np.array([lm.x * w_img, lm.y * h_img])
                
            # Right eye: p1=33, p2=160, p3=158, p4=133, p5=153, p6=144
            re_p1 = get_pt(33)
            re_p2 = get_pt(160)
            re_p3 = get_pt(158)
            re_p4 = get_pt(133)
            re_p5 = get_pt(153)
            re_p6 = get_pt(144)
            
            # Left eye: p1=362, p2=385, p3=387, p4=263, p5=373, p6=380
            le_p1 = get_pt(362)
            le_p2 = get_pt(385)
            le_p3 = get_pt(387)
            le_p4 = get_pt(263)
            le_p5 = get_pt(373)
            le_p6 = get_pt(380)
            
            def compute_ear_eye(p1, p2, p3, p4, p5, p6):
                v1 = np.linalg.norm(p2 - p6)
                v2 = np.linalg.norm(p3 - p5)
                h = np.linalg.norm(p1 - p4)
                if h < 1e-6:
                    return 0.0
                return (v1 + v2) / (2.0 * h)
                
            re_ear = compute_ear_eye(re_p1, re_p2, re_p3, re_p4, re_p5, re_p6)
            le_ear = compute_ear_eye(le_p1, le_p2, le_p3, le_p4, le_p5, le_p6)
            ear = float((re_ear + le_ear) / 2.0)

            # Calculate IPD (interpupillary distance) in pixels using iris centers
            try:
                # Left iris center: 468, Right iris center: 473
                li_lm = face_landmarks[468]
                ri_lm = face_landmarks[473]
                
                lx, ly = li_lm.x * w_img, li_lm.y * h_img
                rx, ry = ri_lm.x * w_img, ri_lm.y * h_img
                
                ipd_pixels = float(np.sqrt((lx - rx) ** 2 + (ly - ry) ** 2))
            except Exception:
                ipd_pixels = None

        # 2. Calculate ambient brightness (YUV Y-channel mean)
        try:
            yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
            y_channel = yuv[:, :, 0]
            avg_brightness = float(np.mean(y_channel))
        except Exception:
            avg_brightness = 120.0  # fallback mid-level brightness

        # 3. Process Pose
        results = self.pose.process(rgb_frame)
        if not results.pose_landmarks:
            return None, None, frame_base64, ear, avg_brightness, ipd_pixels

        # Extract only the key landmarks we care about
        # 0: Nose, 7: Left Ear, 8: Right Ear, 11: Left Shoulder, 12: Right Shoulder
        target_ids = {0, 7, 8, 11, 12}
        extracted_pose_landmarks = {}
        extracted_world_landmarks = {}

        # 1. Screen / Image Normalized landmarks
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            if idx in target_ids:
                extracted_pose_landmarks[idx] = {
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "visibility": landmark.visibility
                }

        # 2. Real-world metric space landmarks (meters)
        if results.pose_world_landmarks:
            for idx, landmark in enumerate(results.pose_world_landmarks.landmark):
                if idx in target_ids:
                    extracted_world_landmarks[idx] = {
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z,
                        "visibility": landmark.visibility
                    }
        else:
            extracted_world_landmarks = None

        return extracted_pose_landmarks, extracted_world_landmarks, frame_base64, ear, avg_brightness, ipd_pixels
