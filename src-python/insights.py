import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Standard location for application user database (completely writeable across environments)
HISTORY_FILE_PATH = os.path.join(os.path.expanduser("~"), ".ergolearn", "posture_history.json")

def load_history() -> List[Dict[str, Any]]:
    """Loads historical posture telemetry logs."""
    if not os.path.exists(HISTORY_FILE_PATH):
        return []
    try:
        with open(HISTORY_FILE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(logs: List[Dict[str, Any]]):
    """Saves historical posture telemetry logs."""
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE_PATH), exist_ok=True)
        with open(HISTORY_FILE_PATH, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Failed to save posture history: {e}")

def append_log_entry(
    score: float, 
    slouching: bool, 
    fhp: bool, 
    asymmetry: bool,
    screen_distance: Optional[float] = None,
    ambient_brightness: Optional[float] = None,
    concentration_index: Optional[float] = None
):
    """Appends a new data point to the history file, keeping it capped at 50,000 entries (approx. 5 days of constant monitoring)."""
    logs = load_history()
    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "slouching": slouching,
        "fhp": fhp,
        "asymmetry": asymmetry,
        "screen_distance": screen_distance,
        "ambient_brightness": ambient_brightness,
        "concentration_index": concentration_index
    }
    logs.append(new_entry)
    
    # Cap size to prevent file bloat
    if len(logs) > 50000:
        logs = logs[-50000:]
        
    save_history(logs)

def fit_linear_regression(x: List[float], y: List[float]) -> float:
    """Fits y = mx + c and returns the slope m."""
    n = len(x)
    if n < 2:
        return 0.0
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(val * val for val in x)
    sum_xy = sum(val_x * val_y for val_x, val_y in zip(x, y))
    
    denom = (n * sum_xx - sum_x * sum_x)
    if abs(denom) < 0.001:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom

def format_hour(hour: int) -> str:
    """Formats 24h index into a clean AM/PM string."""
    if hour == 0:
        return "12:00 AM"
    elif hour < 12:
        return f"{hour}:00 AM"
    elif hour == 12:
        return "12:00 PM"
    else:
        return f"{hour - 12}:00 PM"

def format_time_offset(hour: int, mins_offset: int) -> str:
    """Formulates a break recommendation time index (e.g. 15 -> 3:00 PM minus 15m = 2:45 PM)."""
    h = hour
    m = 60 - mins_offset
    if m >= 60:
        m = 0
    else:
        h -= 1
        
    if h < 0:
        h += 24
        
    am_pm = "PM" if h >= 12 else "AM"
    display_h = h % 12
    if display_h == 0:
        display_h = 12
        
    return f"{display_h}:{str(m).padStart(2, '0') if hasattr(str(m), 'padStart') else str(m).zfill(2)} {am_pm}"

def generate_report() -> Dict[str, Any]:
    """
    Parses local JSON history log data and generates data-driven recommendations,
    hourly profiling charts, and focus vs. healthy posture allocations.
    """
    logs = load_history()
    if len(logs) < 10:
        return {"status": "insufficient_data"}

    # Filter logs to the last 7 days for active reporting
    cutoff_time = datetime.now() - timedelta(days=7)
    parsed_logs = []
    
    for log in logs:
        try:
            log_time = datetime.fromisoformat(log["timestamp"])
            if log_time >= cutoff_time:
                parsed_logs.append((log_time, log))
        except (ValueError, KeyError):
            continue

    if len(parsed_logs) < 10:
        return {"status": "insufficient_data"}

    # --- 1. Hourly Profiling ---
    # Group scores by hour of day (0-23)
    hourly_groups = {}
    for log_time, log in parsed_logs:
        h = log_time.hour
        hourly_groups.setdefault(h, []).append(log["score"])
        
    hourly_averages = []
    for h in sorted(hourly_groups.keys()):
        scores = hourly_groups[h]
        hourly_averages.append({
            "hour": h,
            "label": format_hour(h),
            "score": round(sum(scores) / len(scores), 1)
        })

    # --- 2. Session Fatigue Slope Analysis (Linear Regression) ---
    # Group logs into continuous focus sessions (intervals <= 15 minutes)
    sessions = []
    current_session_times = []
    current_session_scores = []
    last_time = None
    
    for log_time, log in sorted(parsed_logs, key=lambda x: x[0]):
        if last_time is not None and (log_time - last_time) > timedelta(minutes=15):
            if len(current_session_times) >= 10:
                sessions.append((current_session_times, current_session_scores))
            current_session_times = []
            current_session_scores = []
            
        if not current_session_times:
            start_time = log_time
            
        offset_mins = (log_time - start_time).total_seconds() / 60.0
        current_session_times.append(offset_mins)
        current_session_scores.append(log["score"])
        last_time = log_time

    if len(current_session_times) >= 10:
        sessions.append((current_session_times, current_session_scores))

    # Calculate slopes for each session
    slopes = []
    for sx, sy in sessions:
        m = fit_linear_regression(sx, sy)
        slopes.append(m)

    avg_slope = sum(slopes) / len(slopes) if slopes else 0.0
    # Slope is points per minute. Convert to points per hour.
    points_per_hour_drop = -avg_slope * 60.0

    # --- 3. Daily Averages ---
    # Group average score by weekday label
    daily_groups = {}
    weekday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for log_time, log in parsed_logs:
        day_label = weekday_names[log_time.weekday()]
        daily_groups.setdefault(day_label, []).append(log["score"])
        
    # Order daily list to end on today
    today_idx = datetime.now().weekday()
    ordered_days = [weekday_names[(today_idx - i) % 7] for i in range(6, -1, -1)]
    daily_scores = []
    for day in ordered_days:
        scores = daily_groups.get(day, [])
        daily_scores.append({
            "day": day,
            "score": round(sum(scores) / len(scores), 1) if scores else 0.0
        })

    # --- 4. Focus vs. Healthy Posture Allocation ---
    # Assuming each point logged represents approx 10 seconds of active monitoring
    focus_points = len(parsed_logs)
    healthy_points = sum(1 for _, log in parsed_logs if log["score"] >= 85.0)
    
    focus_mins = (focus_points * 10) / 60.0
    healthy_mins = (healthy_points * 10) / 60.0

    # --- 5. Generate AI Recommendations ---
    recommendations = []
    
    # Check for hourly slump
    if len(hourly_averages) >= 2:
        peak_entry = max(hourly_averages, key=lambda x: x["score"])
        # Find slump hour after peak
        future_hours = [x for x in hourly_averages if x["hour"] > peak_entry["hour"]]
        if future_hours:
            slump_entry = min(future_hours, key=lambda x: x["score"])
            drop = peak_entry["score"] - slump_entry["score"]
            if drop >= 10.0:
                drop_pct = round((drop / peak_entry["score"]) * 100)
                slump_str = format_hour(slump_entry["hour"])
                break_str = format_time_offset(slump_entry["hour"], 15)
                recommendations.append(
                    f"Your posture score drops by {drop_pct}% after {slump_str}. We recommend scheduling a standing break at {break_str}."
                )

    # Check for session fatigue
    if points_per_hour_drop >= 6.0:
        recommendations.append(
            f"Fatigue Trend: Your posture quality drops by {round(points_per_hour_drop, 1)} points per hour of sitting. Try taking shorter, more frequent focus intervals."
        )

    # Base profile recommendations
    overall_avg = sum(log["score"] for _, log in parsed_logs) / len(parsed_logs)
    if overall_avg >= 85.0:
        recommendations.append("Excellent alignment profile! You maintain solid ergonomics throughout your sessions.")
    elif overall_avg >= 60.0:
        recommendations.append("Moderate slouching detected. Keep the live posture companion active to help reinforce upright habits.")
    else:
        recommendations.append("High ergonomic strain detected. Review your desk setup height and ensure your keyboard is positioned properly.")

    return {
        "status": "calibrated",
        "recommendations": recommendations,
        "hourly_averages": hourly_averages,
        "daily_scores": daily_scores,
        "focus_vs_healthy": {
            "focus_mins": round(focus_mins),
            "healthy_mins": round(healthy_mins)
        }
    }

def get_personalized_stats_summary(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes detailed statistical breakdown of historical posture and eye telemetry."""
    if not history:
        return {
            "total_entries": 0,
            "avg_score": 0.0,
            "slouch_pct": 0.0,
            "fhp_pct": 0.0,
            "asymmetry_pct": 0.0,
            "avg_screen_dist": None,
            "avg_ambient_light": None,
            "avg_concentration": None,
            "primary_violation": "None"
        }
    
    total = len(history)
    avg_score = sum(h.get("score", 0.0) for h in history) / total
    
    slouch_count = sum(1 for h in history if h.get("slouching", False))
    fhp_count = sum(1 for h in history if h.get("fhp", False))
    asymmetry_count = sum(1 for h in history if h.get("asymmetry", False))
    
    slouch_pct = (slouch_count / total) * 100
    fhp_pct = (fhp_count / total) * 100
    asymmetry_pct = (asymmetry_count / total) * 100
    
    # Calculate averages for optional metrics
    dist_vals = [h["screen_distance"] for h in history if h.get("screen_distance") is not None]
    bright_vals = [h["ambient_brightness"] for h in history if h.get("ambient_brightness") is not None]
    concen_vals = [h["concentration_index"] for h in history if h.get("concentration_index") is not None]
    
    avg_screen_dist = sum(dist_vals) / len(dist_vals) if dist_vals else None
    avg_ambient_light = sum(bright_vals) / len(bright_vals) if bright_vals else None
    avg_concentration = sum(concen_vals) / len(concen_vals) if concen_vals else None
    
    # Primary violation
    violation_pcts = [("slouching", slouch_pct), ("forward head posture", fhp_pct), ("shoulder asymmetry", asymmetry_pct)]
    primary_violation, max_pct = max(violation_pcts, key=lambda x: x[1])
    if max_pct < 10.0:
        primary_violation = "None"
        
    return {
        "total_entries": total,
        "avg_score": round(avg_score, 1),
        "slouch_pct": round(slouch_pct, 1),
        "fhp_pct": round(fhp_pct, 1),
        "asymmetry_pct": round(asymmetry_pct, 1),
        "avg_screen_dist": round(avg_screen_dist, 1) if avg_screen_dist is not None else None,
        "avg_ambient_light": round(avg_ambient_light, 1) if avg_ambient_light is not None else None,
        "avg_concentration": round(avg_concentration, 1) if avg_concentration is not None else None,
        "primary_violation": primary_violation if max_pct >= 10.0 else "None"
    }

def generate_local_ai_response(user_query: str, active_metrics: Optional[Dict[str, Any]] = None) -> str:
    """
    Analyzes user queries locally based on posture logs and replies with personalized
    ergonomic suggestions. Runs when Ollama is offline.
    """
    query = user_query.lower()
    report = generate_report()
    history = load_history()
    stats = get_personalized_stats_summary(history)
    
    # Identify category of query with strict priority
    is_stats_or_score = any(k in query for k in ["score", "stats", "history", "report", "progress", "dashboard", "how am i doing", "performance", "average", "analytics", "chart", "graph"])
    is_break_or_stretch = any(k in query for k in ["break", "stretch", "exercise", "standing", "timer", "schedule", "workout", "yoga", "movement"])
    is_eyes_or_brightness = any(k in query for k in ["eye", "blink", "bright", "light", "tired", "headache", "screen", "distance", "ciliary", "strain", "dry", "fatigue"])
    is_neck_or_back = any(k in query for k in ["neck", "back", "pain", "sore", "shoulder", "slouch", "posture", "ache", "spine", "align", "hunched", "hunch"])
    
    response = ""
    
    # Live session metrics context if active within the last 60 seconds
    live_context = ""
    if active_metrics and active_metrics.get("timestamp"):
        time_diff = datetime.now().timestamp() - active_metrics["timestamp"]
        if time_diff < 60.0:
            live_context = "### ⚡ Live Session Active Context\n"
            live_context += f"- **Current Posture Score:** {active_metrics.get('score', 0):.1f}%\n"
            
            cur_violations = []
            if active_metrics.get("slouching"):
                cur_violations.append("slouching in chair")
            if active_metrics.get("fhp"):
                cur_violations.append("forward head lean (FHP)")
            if active_metrics.get("asymmetry"):
                cur_violations.append("shoulder asymmetry")
                
            if cur_violations:
                live_context += f"- **Current Violations Detected:** {', '.join(cur_violations)} (⚠️ Adjust posture now!)\n"
            else:
                live_context += "- **Current State:** Perfect alignment! Keep it up.\n"
                
            if active_metrics.get("screen_distance") is not None:
                live_context += f"- **Current Screen Distance:** {active_metrics['screen_distance']} cm\n"
            live_context += "\n"

    if is_stats_or_score:
        response += "### 📊 Your Ergonomics Dashboard Summary\n\n"
        if stats["total_entries"] < 10:
            response += f"I don't have enough session history to compile a full dashboard yet (currently: {stats['total_entries']} logs). Keep using the app for a few minutes to start generating report analytics.\n\n"
        else:
            response += f"Here is a summary of your telemetry metrics based on **{stats['total_entries']} logs**:\n\n"
            response += f"- **Average Posture Score:** `{stats['avg_score']}%`\n"
            response += f"- **Slouching Rate:** `{stats['slouch_pct']}%` of session logs\n"
            response += f"- **Forward Head Posture (FHP) Rate:** `{stats['fhp_pct']}%` of session logs\n"
            response += f"- **Shoulder Asymmetry Rate:** `{stats['asymmetry_pct']}%` of session logs\n"
            
            if stats["avg_screen_dist"] is not None:
                response += f"- **Average Screen Distance:** `{stats['avg_screen_dist']} cm`\n"
            if stats["avg_concentration"] is not None:
                response += f"- **Average Concentration index:** `{stats['avg_concentration']}/100`\n"
            
            if report.get("status") == "calibrated" and report.get("recommendations"):
                response += "\n**Key Recommendation:**\n"
                response += f"_{report['recommendations'][0]}_\n\n"
                
        if live_context:
            response += live_context
            
    elif is_break_or_stretch:
        # Determine body part for stretch
        if "neck" in query:
            response += "### 🧘 Custom Neck Release Stretch\n\n"
            response += "Releasing neck fatigue is key to preventing forward head strain:\n\n"
            response += "1. **Chin Tucks (5 reps):** Sit straight, look ahead, and pull your chin straight back (like making a double chin). Hold for 5 seconds, then release.\n"
            response += "2. **Side Neck Stretch (15s each side):** Drop your right ear toward your right shoulder. For a deeper stretch, place your right hand lightly on your head and let gravity pull gently.\n"
            response += "3. **Suboccipital Stretch (15s):** Interlace fingers behind your head, pull elbow points forward, and let the weight of your hands pull your chin down to chest.\n"
        elif "back" in query or "spine" in query:
            response += "### 🧘 Spinal & Back Decompression Stretch\n\n"
            response += "Reverse the slouch and static spinal loads with these movements:\n\n"
            response += "1. **Seated Spinal Twist (15s each side):** Sit tall, place your right hand on your left knee, look over your left shoulder, and gently twist your upper body.\n"
            response += "2. **Chair Cat-Cow (5 reps):** Hands on your knees. Inhale, arch your back, and look up (Cow). Exhale, round your spine, tuck your chin, and roll shoulders forward (Cat).\n"
            response += "3. **Overhead Reach (15s):** Interlace fingers, push palms up to the ceiling, and extend your spine upward as high as comfortable.\n"
        elif "shoulder" in query:
            response += "### 🧘 Shoulder & Chest Opener Stretch\n\n"
            response += "To counteract shoulder roll-in and asymmetry:\n\n"
            response += "1. **Trapezius Shrug & Release (5 reps):** Inhale and pull your shoulders up to your ears. Hold for 3 seconds, then exhale and drop them completely.\n"
            response += "2. **Chest Opener (20s):** Reach your hands behind your back, interlace your fingers, straighten your arms, and lift your chest.\n"
            response += "3. **Shoulder Rolls (10 reps):** Draw large, slow circles with your shoulders, moving them up, back, down, and forward.\n"
        elif "eye" in query or "blink" in query or "strain" in query:
            response += "### 👁️ Eye Muscle Relaxation Routine\n\n"
            response += "Relieve eye muscle fatigue and dryness:\n\n"
            response += "1. **Palming (30s):** Rub your hands together vigorously to warm them. Cup your warm palms over closed eyes without touching the eyeballs, and relax in complete darkness.\n"
            response += "2. **Near-Far Shifting (10 reps):** Hold your thumb 6 inches from your nose. Focus on it for 3 seconds, then shift your gaze to an object 20+ feet away for 3 seconds.\n"
            response += "3. **Blink Recharge:** Close your eyes tightly for 2 seconds, open them, and blink rapidly 10 times to stimulate tear film distribution.\n"
        else:
            response += "### ⏱️ Standing & Stretching Breaks\n\n"
            response += "Frequent micro-movements are the most effective counter to sitting fatigue.\n\n"
            if report.get("status") == "calibrated" and report.get("recommendations"):
                response += "Based on your logs, here are your personalized recommendations:\n"
                for rec in report["recommendations"]:
                    response += f"- {rec}\n"
            else:
                response += "I recommend taking a **5-minute movement break every 45-60 minutes** of sitting.\n"
            response += "\n**Quick Stretch Combo to try right now:**\n"
            response += "- **Chest Opener:** Interlace fingers behind back, stretch arms, and lift chest.\n"
            response += "- **Shoulder Rolls:** Roll shoulders backward in a slow circle 10 times.\n"
            response += "- **Ear-to-Shoulder Neck Release:** Hold for 15 seconds on each side.\n"
            
        if live_context:
            response += "\n" + live_context
            
    elif is_eyes_or_brightness:
        response += "### 👁️ Eye Strain & Vision Ergonomics\n\n"
        
        # Add personalized stats if available
        if stats["avg_screen_dist"] is not None:
            response += "Based on your session tracking history:\n"
            status_dist = "Optimal" if stats["avg_screen_dist"] >= 50 else "⚠️ Too close"
            response += f"- **Average Screen Distance:** `{stats['avg_screen_dist']} cm` ({status_dist})\n"
            response += "\n"
            
        response += "Staring at screens reduces our natural blink rate by up to 50%, leading to dry eyes and ciliary muscle focusing fatigue.\n\n"
        response += "**Actionable Guidelines:**\n"
        response += "- **Maintain Distance:** Ensure your screen is at least **50-70 cm** (about an arm's length) from your face. The camera monitoring will alert you if you lean closer.\n"
        response += "- **The 20-20-20 Rule:** Set a micro-break reminder. Every 20 minutes, look at an object 20 feet away for 20 seconds to relax ciliary muscles.\n"
        response += "- **Ambient Lighting:** Avoid working in dark rooms with high screen contrast. Ensure your environment's brightness matches your screen's output.\n"
        
        if live_context:
            response += "\n" + live_context
            
    elif is_neck_or_back:
        response += "### 🧘 Posture & Neck/Back Strain Analysis\n\n"
        
        if stats["total_entries"] < 10:
            response += "I don't have enough session history to identify specific posture patterns yet. However, back and neck pain usually arise from slouching or forward head protraction (FHP). Check that your screen is elevated and your back is fully supported.\n"
        else:
            response += f"Based on your history of **{stats['total_entries']} logs**, your average posture score is **{stats['avg_score']}%**.\n\n"
            
            # Identify active and historical issues
            issues = []
            if stats["slouch_pct"] > 20:
                issues.append(f"Slouching (`{stats['slouch_pct']}%` of time)")
            if stats["fhp_pct"] > 20:
                issues.append(f"Forward Head Tilt / FHP (`{stats['fhp_pct']}%` of time)")
            if stats["asymmetry_pct"] > 20:
                issues.append(f"Shoulder Asymmetry (`{stats['asymmetry_pct']}%` of time)")
                
            if issues:
                response += f"**Primary Posture Violations Detected:** {', '.join(issues)}.\n\n"
                
            # Tailored advice based on primary historical issue
            primary = stats["primary_violation"]
            response += "**Personalized Corrective Actions:**\n"
            if primary == "slouching":
                response += "- **Seat Depth:** Sit all the way back in your chair so your lumbar region is fully supported by the backrest.\n"
                response += "- **Elbow Placement:** Adjust your armrests or desk height so your elbows bend at a 90-degree angle, keeping keyboard and mouse close.\n"
            elif primary == "forward head posture":
                response += "- **Monitor Height:** Raise your monitor so the top third of the screen is level with your eyes. This prevents neck flexion.\n"
                response += "- **Text Size:** If you lean forward to read, increase the system/browser font scaling to 110% or 120%.\n"
            elif primary == "shoulder asymmetry":
                response += "- **Balance Support:** Ensure your arms are supported equally. Avoid leaning on one side of the desk or resting on a single armrest.\n"
                response += "- **Foot Support:** Keep both feet flat on the floor or on a footrest; avoid crossing your legs, which tilts the pelvis.\n"
            else:
                response += "- **Micro-Adjustments:** Maintain active movement. Try shifting your posture slightly every 15-20 minutes.\n"
                
            response += "- **Quick Stretch:** Do 10 slow shoulder rolls backward to release trapezius muscle tension.\n"
            
        if live_context:
            response += "\n" + live_context
            
    else:
        # Default/Greeting/Help response
        response += "### 🤖 ErgoLearn AI Personal Coach\n\n"
        response += f"Hello! I am your local AI Ergonomic Coach. I analyze your real-time posture logs and camera telemetry to help you build healthy habits.\n\n"
        
        if stats["total_entries"] > 0:
            response += f"I have analyzed **{stats['total_entries']} logs** from your sessions. Your average posture score is **{stats['avg_score']}%**.\n"
            if stats["primary_violation"] != "None":
                response += f"Your main ergonomic issue is **{stats['primary_violation']}**.\n"
            response += "\n"
            
        response += "Ask me questions like:\n"
        response += "- *'Give me a neck stretch'* or *'How can I release shoulder tension?'*\n"
        response += "- *'What does my posture history look like?'* or *'Show my stats'* \n"
        response += "- *'How do I prevent dry eyes?'* or *'Tips for eye fatigue'*\n"
        
        if live_context:
            response += "\n" + live_context
            
    return response
