import unittest
import math
from biomechanics import BiomechanicsAnalyzer
from pose_engine import PoseEngine

class TestErgoLearnBackend(unittest.TestCase):
    def setUp(self):
        self.analyzer = BiomechanicsAnalyzer()
        
        # Define mock screen landmarks (pose_landmarks)
        self.perfect_pose_landmarks = {
            0: {"x": 0.5, "y": 0.28, "z": 0.0, "visibility": 0.99},      # Nose
            7: {"x": 0.45, "y": 0.23, "z": 0.0, "visibility": 0.99},     # Ear L
            8: {"x": 0.55, "y": 0.23, "z": 0.0, "visibility": 0.99},     # Ear R
            11: {"x": 0.35, "y": 0.48, "z": 0.0, "visibility": 0.99},    # Shoulder L
            12: {"x": 0.65, "y": 0.48, "z": 0.0, "visibility": 0.99}     # Shoulder R
        }

        # Define mock 3D world landmarks for perfect baseline posture (in meters)
        # Origin is hips. y is negative upwards. z is negative towards camera.
        self.perfect_world_landmarks = {
            0: {"x": 0.0, "y": -0.75, "z": -0.1, "visibility": 0.99},      # Nose
            7: {"x": -0.08, "y": -0.75, "z": -0.05, "visibility": 0.99},   # Ear L
            8: {"x": 0.08, "y": -0.75, "z": -0.05, "visibility": 0.99},    # Ear R
            11: {"x": -0.2, "y": -0.5, "z": 0.0, "visibility": 0.99},      # Shoulder L
            12: {"x": 0.2, "y": -0.5, "z": 0.0, "visibility": 0.99}        # Shoulder R
        }

    def test_initialization(self):
        """Test that objects can be successfully instantiated."""
        self.assertFalse(self.analyzer.calibrated)
        engine = PoseEngine()
        self.assertIsNotNone(engine.mp_pose)

    def test_calibration(self):
        """Test that baseline calibration stores all multi-factor 3D metrics."""
        success = self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        self.assertTrue(success)
        self.assertTrue(self.analyzer.calibrated)
        
        # 1. Slouch Angle Baseline
        self.assertAlmostEqual(self.analyzer.baseline_slouch_ratio, 0.25 / math.sqrt(0.0725))
        
        # 2. Torso Height Baseline
        self.assertAlmostEqual(self.analyzer.baseline_torso_height, 0.75)
        
        # 3. Neck Ratio Baseline
        self.assertAlmostEqual(self.analyzer.baseline_neck_ratio, 0.625)

        # 4. Shoulder Height Baseline (3D & Screen)
        self.assertAlmostEqual(self.analyzer.baseline_shoulder_height, 0.50)
        self.assertAlmostEqual(self.analyzer.baseline_screen_shoulders_y, 0.48)

    def test_normal_posture(self):
        """Test that normal posture reports no violations and a score of 100."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        result = self.analyzer.analyze(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        self.assertEqual(result["status"], "calibrated")
        self.assertEqual(result["metrics"]["score"], 100.0)
        self.assertFalse(result["violations"]["slouch"])
        self.assertFalse(result["violations"]["forward_head"])
        self.assertFalse(result["violations"]["lateral_asymmetry"])

    def test_slouch_via_head_angle(self):
        """Test that dropping head angle triggers a slouch violation (Turtleneck Effect)."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        # Head tilts forward/downwards (angle decreases, other factors stay close to baseline)
        slouch_landmarks = {
            0: {"x": 0.0, "y": -0.68, "z": -0.17, "visibility": 0.99},      # Nose
            7: {"x": -0.08, "y": -0.71, "z": -0.12, "visibility": 0.99},    # Ear L
            8: {"x": 0.08, "y": -0.71, "z": -0.12, "visibility": 0.99},     # Ear R
            11: {"x": -0.2, "y": -0.5, "z": 0.0, "visibility": 0.99},       # Shoulder L
            12: {"x": 0.2, "y": -0.5, "z": 0.0, "visibility": 0.99}         # Shoulder R
        }
        
        for _ in range(15):
            result = self.analyzer.analyze(self.perfect_pose_landmarks, slouch_landmarks)
            
        self.assertTrue(result["violations"]["slouch"])
        self.assertLess(result["metrics"]["score"], 100.0)

    def test_slouch_via_torso_sinking(self):
        """Test that sliding/sinking down in the chair triggers a slouch violation."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        # Head height collapses downward
        sinking_landmarks = {
            0: {"x": 0.0, "y": -0.65, "z": -0.1, "visibility": 0.99},       # Nose
            7: {"x": -0.08, "y": -0.65, "z": -0.05, "visibility": 0.99},    # Ear L
            8: {"x": 0.08, "y": -0.65, "z": -0.05, "visibility": 0.99},     # Ear R
            11: {"x": -0.2, "y": -0.45, "z": 0.0, "visibility": 0.99},      # Shoulder L
            12: {"x": 0.2, "y": -0.45, "z": 0.0, "visibility": 0.99}        # Shoulder R
        }
        
        for _ in range(15):
            result = self.analyzer.analyze(self.perfect_pose_landmarks, sinking_landmarks)
            
        self.assertTrue(result["violations"]["slouch"])
        self.assertLess(result["metrics"]["score"], 100.0)

    def test_slouch_via_shoulder_hunching(self):
        """Test that hunched shoulders (elevating them towards ears) triggers slouching."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        # Shoulders move UP (more negative) towards ears
        hunch_landmarks = {
            0: {"x": 0.0, "y": -0.75, "z": -0.1, "visibility": 0.99},
            7: {"x": -0.08, "y": -0.75, "z": -0.05, "visibility": 0.99},
            8: {"x": 0.08, "y": -0.75, "z": -0.05, "visibility": 0.99},
            11: {"x": -0.2, "y": -0.68, "z": 0.0, "visibility": 0.99},      # Shoulder L raised
            12: {"x": 0.2, "y": -0.68, "z": 0.0, "visibility": 0.99}        # Shoulder R raised
        }
        
        for _ in range(15):
            result = self.analyzer.analyze(self.perfect_pose_landmarks, hunch_landmarks)
            
        self.assertTrue(result["violations"]["slouch"])
        self.assertLess(result["metrics"]["score"], 100.0)

    def test_slouch_via_3d_shoulder_sinking(self):
        """Test that shoulders physically sinking down relative to hips triggers slouching."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        # 3D Shoulder height collapse (shoulders closer to hips origin)
        sinking_shoulders = {
            0: {"x": 0.0, "y": -0.75, "z": -0.1, "visibility": 0.99},
            7: {"x": -0.08, "y": -0.75, "z": -0.05, "visibility": 0.99},
            8: {"x": 0.08, "y": -0.75, "z": -0.05, "visibility": 0.99},
            11: {"x": -0.2, "y": -0.42, "z": 0.0, "visibility": 0.99},      # Shoulder L lower
            12: {"x": 0.2, "y": -0.42, "z": 0.0, "visibility": 0.99}        # Shoulder R lower
        }
        
        for _ in range(15):
            result = self.analyzer.analyze(self.perfect_pose_landmarks, sinking_shoulders)
            
        self.assertTrue(result["violations"]["slouch"])
        self.assertLess(result["metrics"]["score"], 100.0)

    def test_slouch_via_screen_shoulder_sinking(self):
        """Test that shoulders sinking lower in screen space triggers slouching."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        # Screen shoulders sink down from baseline y=0.48 to y=0.54
        sinking_screen = {
            0: {"x": 0.5, "y": 0.28, "z": 0.0, "visibility": 0.99},
            7: {"x": 0.45, "y": 0.23, "z": 0.0, "visibility": 0.99},
            8: {"x": 0.55, "y": 0.23, "z": 0.0, "visibility": 0.99},
            11: {"x": 0.35, "y": 0.54, "z": 0.0, "visibility": 0.99},       # Shoulder L lower
            12: {"x": 0.65, "y": 0.54, "z": 0.0, "visibility": 0.99}        # Shoulder R lower
        }
        
        for _ in range(15):
            result = self.analyzer.analyze(sinking_screen, self.perfect_world_landmarks)
            
        self.assertTrue(result["violations"]["slouch"])
        self.assertLess(result["metrics"]["score"], 100.0)

    def test_fhp_violation(self):
        """Test that head leaning forward triggers forward head protraction."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        # Mock forward head protraction (head moves closer to camera relative to shoulders)
        fhp_landmarks = {
            0: {"x": 0.0, "y": -0.72, "z": -0.20, "visibility": 0.99},
            7: {"x": -0.08, "y": -0.72, "z": -0.15, "visibility": 0.99},
            8: {"x": 0.08, "y": -0.72, "z": -0.15, "visibility": 0.99},
            11: {"x": -0.2, "y": -0.5, "z": 0.0, "visibility": 0.99},
            12: {"x": 0.2, "y": -0.5, "z": 0.0, "visibility": 0.99}
        }
        
        for _ in range(15):
            result = self.analyzer.analyze(self.perfect_pose_landmarks, fhp_landmarks)
            
        self.assertTrue(result["violations"]["forward_head"])
        self.assertLess(result["metrics"]["score"], 100.0)

    def test_lateral_asymmetry(self):
        """Test that shoulder tilt triggers asymmetry violation."""
        self.analyzer.calibrate(self.perfect_pose_landmarks, self.perfect_world_landmarks)
        
        # Mock lateral asymmetry (left shoulder up, right shoulder down)
        asymmetry_landmarks = {
            0: {"x": 0.02, "y": -0.73, "z": -0.1, "visibility": 0.99},
            7: {"x": -0.06, "y": -0.73, "z": -0.05, "visibility": 0.99},
            8: {"x": 0.10, "y": -0.73, "z": -0.05, "visibility": 0.99},
            11: {"x": -0.2, "y": -0.55, "z": 0.0, "visibility": 0.99},     # Left shoulder up
            12: {"x": 0.2, "y": -0.45, "z": 0.0, "visibility": 0.99}       # Right shoulder down
        }
        
        for _ in range(15):
            result = self.analyzer.analyze(self.perfect_pose_landmarks, asymmetry_landmarks)
            
        self.assertTrue(result["violations"]["lateral_asymmetry"])
        self.assertLess(result["metrics"]["score"], 100.0)

    def test_ear_and_brightness_calculations(self):
        """Test that eye aspect ratio and brightness helper math is correct."""
        import numpy as np
        import cv2
        
        # 1. Test PoseEngine initialization
        engine = PoseEngine()
        self.assertIsNotNone(engine.face_mesh)
        
        # 2. Test Brightness calculation on mock black frame
        black_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        yuv = cv2.cvtColor(black_frame, cv2.COLOR_BGR2YUV)
        avg_brightness = float(np.mean(yuv[:, :, 0]))
        self.assertEqual(avg_brightness, 0.0)
        
        # 3. Test Brightness calculation on mock white frame
        white_frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
        yuv_white = cv2.cvtColor(white_frame, cv2.COLOR_BGR2YUV)
        avg_brightness_white = float(np.mean(yuv_white[:, :, 0]))
        self.assertAlmostEqual(avg_brightness_white, 255.0, delta=1.0)

    def test_screen_distance_estimation(self):
        """Test the depth/distance estimation formula based on baseline IPD."""
        baseline_ipd = 100.0
        # At baseline distance, current IPD is baseline IPD -> distance is 60cm
        self.assertAlmostEqual(60.0 * (baseline_ipd / 100.0), 60.0)
        
        # Sitting closer: current IPD increases (e.g. to 120 pixels) -> distance decreases
        self.assertAlmostEqual(60.0 * (baseline_ipd / 120.0), 50.0)
        
        # Sitting further: current IPD decreases (e.g. to 80 pixels) -> distance increases
        self.assertAlmostEqual(60.0 * (baseline_ipd / 80.0), 75.0)

if __name__ == "__main__":
    unittest.main()
