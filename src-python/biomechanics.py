import math
from typing import Dict, Any, Tuple, Optional

class BiomechanicsAnalyzer:
    def __init__(self):
        # Baseline variables saved during calibration
        self.calibrated = False
        self.baseline_slouch_ratio: float = 0.0
        self.baseline_torso_height: float = 0.0
        self.baseline_neck_ratio: float = 0.0
        self.baseline_fhp_ratio: float = 0.0
        self.baseline_shoulder_height: float = 0.0
        self.baseline_screen_shoulders_y: float = 0.0
        
        # Exponential Moving Average (EMA) smoothing variables
        self.smoothed_slouch_fraction: Optional[float] = None
        self.smoothed_fhp_fraction: Optional[float] = None
        self.smoothed_shoulder_slope: Optional[float] = None
        self.smoothed_score: Optional[float] = None
        
        # Smoothing coefficient (increased to 0.25 for snappier, more responsive posture tracking)
        self.ALPHA = 0.25 
        
        # Hysteresis state flags (remembers violation status to prevent boundary flickering)
        self.is_slouching = False
        self.is_fhp = False
        self.is_asymmetric = False
        
        # Hysteresis Thresholds (optimized for multi-factor 3D indicators)
        self.SLOUCH_TRIGGER = 0.90  # Triggers if any factor drops by 10% or more (90% threshold)
        self.SLOUCH_RECOVER = 0.93  # Recovers when all indicators return to 93% or higher
        
        self.FHP_TRIGGER = 1.15     # Head depth forward displacement exceeds 15% of shoulder width
        self.FHP_RECOVER = 1.10     # Recovers below 10%
        
        self.ASYMMETRY_TRIGGER = 0.15 # Slope threshold relative to 3D shoulder width
        self.ASYMMETRY_RECOVER = 0.09 # Slope recovery threshold

    def calibrate(self, pose_landmarks: Dict[int, Dict[str, float]], world_landmarks: Dict[int, Dict[str, float]]) -> bool:
        """
        Calibrates the baseline using screen pose_landmarks and 3D world_landmarks.
        """
        try:
            # 1. Shoulder Midpoint & Width in 3D (meters)
            x_mid = (world_landmarks[11]['x'] + world_landmarks[12]['x']) / 2.0
            y_mid = (world_landmarks[11]['y'] + world_landmarks[12]['y']) / 2.0
            z_mid = (world_landmarks[11]['z'] + world_landmarks[12]['z']) / 2.0
            
            shoulder_width = math.sqrt(
                (world_landmarks[11]['x'] - world_landmarks[12]['x'])**2 +
                (world_landmarks[11]['y'] - world_landmarks[12]['y'])**2 +
                (world_landmarks[11]['z'] - world_landmarks[12]['z'])**2
            )
            shoulder_width = max(0.01, shoulder_width)
            
            # 2. Nose vector relative to shoulder midpoint (meters)
            vx = world_landmarks[0]['x'] - x_mid
            vy = world_landmarks[0]['y'] - y_mid
            vz = world_landmarks[0]['z'] - z_mid
            vec_len = math.sqrt(vx**2 + vy**2 + vz**2)
            
            # 3. Baseline Slouch Alignment Angle (cos theta relative to vertical up vector (0, -1, 0))
            self.baseline_slouch_ratio = -vy / max(0.001, vec_len)
            
            # 4. Baseline Torso Height (-y_nose in world coordinates relative to hips origin)
            self.baseline_torso_height = -world_landmarks[0]['y']
            
            # 5. Baseline Neck Height (ear-to-shoulder vertical distance normalized by shoulder width)
            y_ear = (world_landmarks[7]['y'] + world_landmarks[8]['y']) / 2.0
            h_neck = y_mid - y_ear
            self.baseline_neck_ratio = h_neck / shoulder_width
            
            # 6. Baseline FHP
            self.baseline_fhp_ratio = (z_mid - world_landmarks[0]['z']) / shoulder_width

            # 7. Baseline 3D Shoulder Height (vertical distance above hips in meters)
            self.baseline_shoulder_height = -y_mid

            # 8. Baseline Screen Shoulders Y (normalized screen space)
            self.baseline_screen_shoulders_y = (pose_landmarks[11]['y'] + pose_landmarks[12]['y']) / 2.0
            
            # Reset history
            self.smoothed_slouch_fraction = None
            self.smoothed_fhp_fraction = None
            self.smoothed_shoulder_slope = None
            self.smoothed_score = None
            self.is_slouching = False
            self.is_fhp = False
            self.is_asymmetric = False
            
            self.calibrated = True
            return True
        except KeyError:
            return False

    def analyze(self, pose_landmarks: Dict[int, Dict[str, float]], world_landmarks: Dict[int, Dict[str, float]]) -> Dict[str, Any]:
        """
        Analyzes the current posture frame against the baseline using screen and world landmarks.
        """
        if not self.calibrated:
            return {"status": "uncalibrated"}
            
        try:
            # 1. Compute 3D variables (meters)
            x_mid = (world_landmarks[11]['x'] + world_landmarks[12]['x']) / 2.0
            y_mid = (world_landmarks[11]['y'] + world_landmarks[12]['y']) / 2.0
            z_mid = (world_landmarks[11]['z'] + world_landmarks[12]['z']) / 2.0
            
            current_shoulder_width = math.sqrt(
                (world_landmarks[11]['x'] - world_landmarks[12]['x'])**2 +
                (world_landmarks[11]['y'] - world_landmarks[12]['y'])**2 +
                (world_landmarks[11]['z'] - world_landmarks[12]['z'])**2
            )
            current_shoulder_width = max(0.01, current_shoulder_width)
            
            # Nose vector
            vx = world_landmarks[0]['x'] - x_mid
            vy = world_landmarks[0]['y'] - y_mid
            vz = world_landmarks[0]['z'] - z_mid
            vec_len = math.sqrt(vx**2 + vy**2 + vz**2)
            
            # Indicator A: Head-to-Shoulder Slouch Angle
            current_alignment = -vy / max(0.001, vec_len)
            fraction_angle = current_alignment / max(0.001, self.baseline_slouch_ratio)
            
            # Indicator B: Torso Sinking (Spine collapse/slide)
            current_torso_height = -world_landmarks[0]['y']
            fraction_torso = current_torso_height / max(0.01, self.baseline_torso_height)
            
            # Indicator C: Shoulder Elevation / Hunching (ear-to-shoulder vertical compression)
            y_ear = (world_landmarks[7]['y'] + world_landmarks[8]['y']) / 2.0
            current_h_neck = y_mid - y_ear
            current_neck_ratio = current_h_neck / current_shoulder_width
            fraction_hunch = current_neck_ratio / max(0.01, self.baseline_neck_ratio)

            # Indicator D: 3D Shoulder Height (meters above hips)
            current_shoulder_height = -y_mid
            fraction_shoulder_height = current_shoulder_height / max(0.01, self.baseline_shoulder_height)

            # Indicator E: Screen-Space Shoulder Sinking (with 2x sensitivity multiplier)
            current_screen_shoulders_y = (pose_landmarks[11]['y'] + pose_landmarks[12]['y']) / 2.0
            fraction_screen_shoulders = 1.0 - 2.0 * (current_screen_shoulders_y - self.baseline_screen_shoulders_y)
            fraction_screen_shoulders = min(1.0, max(0.0, fraction_screen_shoulders))
            
            # Overall slouch fraction is the minimum of all visual cues, capped at 1.0
            slouch_fraction = min(1.0, fraction_angle, fraction_torso, fraction_hunch, fraction_shoulder_height, fraction_screen_shoulders)
            
            # 2. Current 3D FHP ratio
            current_fhp = (z_mid - world_landmarks[0]['z']) / current_shoulder_width
            fhp_fraction = 1.0 + (current_fhp - self.baseline_fhp_ratio)
            
            # 3. Current 3D rotation-invariant shoulder slope
            shoulder_slope = (world_landmarks[12]['y'] - world_landmarks[11]['y']) / current_shoulder_width

            # 4. Apply Temporal EMA Smoothing to filter out noise
            if self.smoothed_slouch_fraction is None:
                self.smoothed_slouch_fraction = slouch_fraction
                self.smoothed_fhp_fraction = fhp_fraction
                self.smoothed_shoulder_slope = shoulder_slope
            else:
                self.smoothed_slouch_fraction = self.ALPHA * slouch_fraction + (1.0 - self.ALPHA) * self.smoothed_slouch_fraction
                self.smoothed_fhp_fraction = self.ALPHA * fhp_fraction + (1.0 - self.ALPHA) * self.smoothed_fhp_fraction
                self.smoothed_shoulder_slope = self.ALPHA * shoulder_slope + (1.0 - self.ALPHA) * self.smoothed_shoulder_slope

            # 5. Evaluate Violations using Hysteresis (Anti-Flicker)
            # Slouching state
            if not self.is_slouching:
                if self.smoothed_slouch_fraction < self.SLOUCH_TRIGGER:
                    self.is_slouching = True
            else:
                if self.smoothed_slouch_fraction > self.SLOUCH_RECOVER:
                    self.is_slouching = False

            # Forward Head state
            if not self.is_fhp:
                if self.smoothed_fhp_fraction > self.FHP_TRIGGER:
                    self.is_fhp = True
            else:
                if self.smoothed_fhp_fraction < self.FHP_RECOVER:
                    self.is_fhp = False

            # Lateral Asymmetry state
            if not self.is_asymmetric:
                if abs(self.smoothed_shoulder_slope) > self.ASYMMETRY_TRIGGER:
                    self.is_asymmetric = True
            else:
                if abs(self.smoothed_shoulder_slope) < self.ASYMMETRY_RECOVER:
                    self.is_asymmetric = False

            # 6. Calculate Score with dynamic severity scaling (allows score to drop down to 0%)
            score = 100.0
            deductions = 0.0
            
            if self.is_slouching:
                # Base deduction of 40, scaling up to 100 based on slouch severity
                severity = (self.SLOUCH_TRIGGER - self.smoothed_slouch_fraction) / self.SLOUCH_TRIGGER
                severity = max(0.0, min(1.0, severity))
                deductions += 40.0 + 60.0 * severity
                
            if self.is_fhp:
                # Base deduction of 30, scaling up based on FHP severity
                severity = (self.smoothed_fhp_fraction - self.FHP_TRIGGER) / 0.30
                severity = max(0.0, min(1.0, severity))
                deductions += 30.0 + 70.0 * severity
                
            if self.is_asymmetric:
                # Base deduction of 30, scaling up based on shoulder slope severity
                severity = (abs(self.smoothed_shoulder_slope) - self.ASYMMETRY_TRIGGER) / 0.15
                severity = max(0.0, min(1.0, severity))
                deductions += 30.0 + 70.0 * severity

            raw_score = max(0.0, score - deductions)

            if self.smoothed_score is None:
                self.smoothed_score = raw_score
            else:
                self.smoothed_score = self.ALPHA * raw_score + (1.0 - self.ALPHA) * self.smoothed_score

            return {
                "status": "calibrated",
                "metrics": {
                    "slouch_ratio": round(self.smoothed_slouch_fraction, 3),
                    "fhp_deviation": round(self.smoothed_fhp_fraction, 3),
                    "shoulder_slope": round(self.smoothed_shoulder_slope, 3),
                    "score": round(self.smoothed_score, 1)
                },
                "violations": {
                    "slouch": self.is_slouching,
                    "forward_head": self.is_fhp,
                    "lateral_asymmetry": self.is_asymmetric
                }
            }
        except KeyError:
            return {"status": "error", "message": "Missing required joints in landmarks"}

    def _distance(self, p1: Dict[str, float], p2: Dict[str, float]) -> float:
        return math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
