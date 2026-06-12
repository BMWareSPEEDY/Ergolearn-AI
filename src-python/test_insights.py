import unittest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
import insights

class TestErgoInsights(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for safe test database usage
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_posture_history.json")
        # Override the history file path in insights module
        insights.HISTORY_FILE_PATH = self.test_file

    def tearDown(self):
        # Clean up temporary test files
        shutil.rmtree(self.test_dir)

    def test_fit_linear_regression(self):
        # Linear curve: y = -2x + 100
        x = [0.0, 10.0, 20.0, 30.0, 40.0]
        y = [100.0, 80.0, 60.0, 40.0, 20.0]
        slope = insights.fit_linear_regression(x, y)
        self.assertAlmostEqual(slope, -2.0)

        # Flat curve: y = 80
        y_flat = [80.0, 80.0, 80.0, 80.0, 80.0]
        slope_flat = insights.fit_linear_regression(x, y_flat)
        self.assertAlmostEqual(slope_flat, 0.0)

        # Less than 2 points
        self.assertAlmostEqual(insights.fit_linear_regression([1.0], [5.0]), 0.0)

    def test_append_log_and_load(self):
        # Ensure starts empty
        logs = insights.load_history()
        self.assertEqual(len(logs), 0)

        # Append entry
        insights.append_log_entry(95.0, False, False, False)
        logs = insights.load_history()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["score"], 95.0)
        self.assertFalse(logs[0]["slouching"])

    def test_generate_report_insufficient_data(self):
        # Less than 10 points
        for i in range(5):
            insights.append_log_entry(90.0, False, False, False)
        report = insights.generate_report()
        self.assertEqual(report["status"], "insufficient_data")

    def test_generate_report_calibrated(self):
        # Write mock data over the last 7 days to trigger full calculations
        now = datetime.now()
        
        # 1. Simulate 50 log entries spread over the last few days
        # Log active sessions of posture scores dropping over time (fatigue slope)
        for day_offset in range(3):
            session_start = now - timedelta(days=day_offset, hours=4)
            for i in range(20):
                log_time = session_start + timedelta(minutes=i * 10)
                # Score drops from 95 to 70 over 200 minutes (approx 1.25 hours)
                score = 95.0 - (i * 1.3) 
                
                # Mock entry creation
                entry = {
                    "timestamp": log_time.isoformat(),
                    "score": score,
                    "slouching": score < 75.0,
                    "fhp": False,
                    "asymmetry": False
                }
                logs = insights.load_history()
                logs.append(entry)
                insights.save_history(logs)

        # 2. Append standard logs to simulate a time-of-day slump
        # peak score at 10:00 AM (e.g. 95%), slump score at 3:00 PM (e.g. 60%)
        # Let's add them directly
        logs = insights.load_history()
        for hour, score in [(10, 95.0), (10, 93.0), (15, 60.0), (15, 62.0)]:
            log_time = now.replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=1)
            logs.append({
                "timestamp": log_time.isoformat(),
                "score": score,
                "slouching": score < 75.0,
                "fhp": False,
                "asymmetry": False
            })
        insights.save_history(logs)

        # Generate report
        report = insights.generate_report()
        
        self.assertEqual(report["status"], "calibrated")
        self.assertIn("recommendations", report)
        self.assertIn("hourly_averages", report)
        self.assertIn("daily_scores", report)
        self.assertIn("focus_vs_healthy", report)

        # Verify hourly averages are calculated
        self.assertTrue(len(report["hourly_averages"]) > 0)
        self.assertTrue(len(report["daily_scores"]) > 0)

        # Validate recommendations are present and contain fatigue or slump statements
        recs = report["recommendations"]
        self.assertTrue(any("drops by" in rec or "slump" in rec or "break" in rec for rec in recs))

    def test_local_ai_response(self):
        # 1. Test insufficient data fallback
        resp = insights.generate_local_ai_response("neck pain")
        self.assertIn("don't have enough session history", resp)

        # 2. Add some mock logs to history
        insights.append_log_entry(80.0, True, False, False)
        insights.append_log_entry(85.0, False, False, False)

        # 3. Test different user query categories
        resp_neck = insights.generate_local_ai_response("sore neck")
        self.assertIn("Posture & Neck/Back Strain Analysis", resp_neck)

        resp_eyes = insights.generate_local_ai_response("eye fatigue")
        self.assertIn("Eye Strain & Vision Ergonomics", resp_eyes)

        resp_stretch = insights.generate_local_ai_response("give me a stretch")
        self.assertIn("Standing & Stretching Breaks", resp_stretch)

        # Test specific target stretch
        resp_neck_stretch = insights.generate_local_ai_response("Give me a quick neck stretch")
        self.assertIn("Custom Neck Release Stretch", resp_neck_stretch)
        self.assertIn("Chin Tucks", resp_neck_stretch)

        resp_stats = insights.generate_local_ai_response("show my progress")
        self.assertIn("Your Ergonomics Dashboard Summary", resp_stats)

        resp_help = insights.generate_local_ai_response("hello")
        self.assertIn("ErgoLearn AI Personal Coach", resp_help)

        # 4. Test live session active context injection
        import time
        active_metrics = {
            "score": 75.0,
            "slouching": True,
            "fhp": False,
            "asymmetry": False,
            "screen_distance": 45.0,
            "timestamp": time.time()
        }
        resp_live = insights.generate_local_ai_response("show my progress", active_metrics=active_metrics)
        self.assertIn("Live Session Active Context", resp_live)
        self.assertIn("Current Posture Score:** 75.0%", resp_live)
        self.assertIn("slouching in chair", resp_live)
        self.assertIn("Current Screen Distance:** 45.0 cm", resp_live)

if __name__ == "__main__":
    unittest.main()
