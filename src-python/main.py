import asyncio
import json
import logging
import sys
from typing import Optional, Dict, Any, List
from websockets.server import serve
from pose_engine import PoseEngine
from biomechanics import BiomechanicsAnalyzer
import time
from insights import append_log_entry, generate_report, generate_local_ai_response, get_personalized_stats_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ErgoLearnBackend")

# Initialize core engines
pose_engine = PoseEngine()
analyzer = BiomechanicsAnalyzer()

# Global state
is_monitoring = False
calibration_countdown = 0
baseline_ipd = None
calibration_ipds = []
last_active_metrics = {
    "score": None,
    "slouching": False,
    "fhp": False,
    "asymmetry": False,
    "screen_distance": None,
    "ambient_brightness": None,
    "concentration_index": None,
    "timestamp": None
}

async def monitoring_loop(websocket):
    global is_monitoring, calibration_countdown, baseline_ipd, last_active_metrics
    logger.info("Starting monitoring loop...")
    
    # Open camera
    if not pose_engine.start_camera():
        logger.error("Failed to open camera device.")
        await websocket.send(json.dumps({"type": "error", "message": "Failed to access webcam."}))
        is_monitoring = False
        return

    stable_count = 0
    last_log_time = time.time()
    posture_scores_rolling = []
    
    try:
        while is_monitoring:
            pose_landmarks, world_landmarks, frame_base64, ear, avg_brightness, ipd_pixels = pose_engine.capture_frame()
            
            if frame_base64:

                # Handle active calibration state
                if calibration_countdown > 0:
                    if world_landmarks and pose_landmarks:
                        analyzer.calibrate(pose_landmarks, world_landmarks)
                    if ipd_pixels is not None:
                        calibration_ipds.append(ipd_pixels)
                    calibration_countdown -= 1
                    await websocket.send(json.dumps({
                        "type": "calibration_progress",
                        "remaining": calibration_countdown,
                        "landmarks": pose_landmarks,
                        "frame": frame_base64,
                        "timestamp": int(time.time() * 1000)
                    }))
                    if calibration_countdown == 0:
                        if calibration_ipds:
                            baseline_ipd = sum(calibration_ipds) / len(calibration_ipds)
                            logger.info(f"Calibration complete. Baseline IPD: {baseline_ipd:.2f} pixels")
                        else:
                            baseline_ipd = None
                            logger.warning("Calibration complete but no IPD data collected.")
                        await websocket.send(json.dumps({"type": "calibration_complete"}))
                    await asyncio.sleep(0.5)
                    continue

                # Normal monitoring
                if world_landmarks and pose_landmarks:
                    analysis_results = analyzer.analyze(pose_landmarks, world_landmarks)
                else:
                    analysis_results = {"status": "no_pose", "message": "No joints detected"}
                
                # Compute screen distance
                screen_distance = None
                if baseline_ipd is not None and ipd_pixels is not None and ipd_pixels > 0:
                    screen_distance = 60.0 * (baseline_ipd / ipd_pixels)
                
                # Compute Concentration Index
                concentration_index = 100.0
                if world_landmarks and pose_landmarks and analysis_results.get("status") == "calibrated":
                    posture_score = analysis_results["metrics"]["score"]
                    posture_scores_rolling.append((time.time(), posture_score))
                    
                    # Filter out entries older than 10 seconds (optimized for higher responsiveness)
                    now = time.time()
                    posture_scores_rolling = [item for item in posture_scores_rolling if now - item[0] <= 10.0]
                    
                    if posture_scores_rolling:
                        concentration_index = round(sum(item[1] for item in posture_scores_rolling) / len(posture_scores_rolling), 1)
                else:
                    concentration_index = 0.0

                # Inject extended metrics into calibrated analysis results and update live metrics state
                if analysis_results.get("status") == "calibrated":
                    analysis_results["metrics"]["ambient_brightness"] = round(avg_brightness, 1)
                    analysis_results["metrics"]["concentration_index"] = concentration_index
                    analysis_results["metrics"]["screen_distance"] = round(screen_distance, 1) if screen_distance is not None else None
                    
                    # Update global live metrics state
                    last_active_metrics["score"] = analysis_results["metrics"]["score"]
                    last_active_metrics["slouching"] = analysis_results["violations"]["slouch"]
                    last_active_metrics["fhp"] = analysis_results["violations"]["forward_head"]
                    last_active_metrics["asymmetry"] = analysis_results["violations"]["lateral_asymmetry"]
                    last_active_metrics["screen_distance"] = analysis_results["metrics"]["screen_distance"]
                    last_active_metrics["ambient_brightness"] = analysis_results["metrics"]["ambient_brightness"]
                    last_active_metrics["concentration_index"] = concentration_index
                    last_active_metrics["timestamp"] = time.time()
                
                # Check for stable state to throttle frame rates (Resource Throttling)
                sleep_interval = 0.005  # run at full camera hardware frame rate (minimal async yield sleep)
                
                if world_landmarks and pose_landmarks and analysis_results.get("status") == "calibrated":
                    score = analysis_results["metrics"]["score"]
                    is_violating = any(analysis_results["violations"].values())
                    
                    if score >= 90 and not is_violating:
                        stable_count += 1
                    else:
                        stable_count = 0
                        
                    # If stable for more than 40 frames, throttle slightly to ~30 FPS (0.033s sleep) to reduce CPU load
                    if stable_count > 40:
                        sleep_interval = 0.033
                else:
                    stable_count = 0
                
                # Log telemetry once every 10 seconds of active monitoring
                current_time = time.time()
                if current_time - last_log_time >= 10.0:
                    if world_landmarks and pose_landmarks and analysis_results.get("status") == "calibrated":
                        score = analysis_results["metrics"]["score"]
                        violations = analysis_results["violations"]
                        append_log_entry(
                            score,
                            violations["slouch"],
                            violations["forward_head"],
                            violations["lateral_asymmetry"],
                            screen_distance=analysis_results["metrics"]["screen_distance"],
                            ambient_brightness=analysis_results["metrics"]["ambient_brightness"],
                            concentration_index=concentration_index
                        )
                        last_log_time = current_time
                
                payload = {
                    "type": "posture_update",
                    "landmarks": pose_landmarks,
                    "frame": frame_base64,
                    "analysis": analysis_results,
                    "eye_metrics": {
                        "ambient_brightness": round(avg_brightness, 1),
                        "concentration_index": concentration_index,
                        "screen_distance": round(screen_distance, 1) if screen_distance is not None else None
                    },
                    "timestamp": int(time.time() * 1000)
                }
                await websocket.send(json.dumps(payload))
                await asyncio.sleep(sleep_interval)
            else:
                # Frame read failed, wait briefly before retrying
                await asyncio.sleep(0.1)
                
    except Exception as e:
        logger.error(f"Error in monitoring loop: {e}")
    finally:
        pose_engine.stop_camera()
        logger.info("Camera released. Monitoring loop stopped.")

async def query_local_ollama(user_query: str) -> Optional[str]:
    import urllib.request
    import json
    
    def get_model():
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = data.get("models", [])
                    # Prefer qwen3.5:0.8b if available
                    names = [m.get("name", "") for m in models]
                    for name in names:
                        if "qwen3.5:0.8b" in name:
                            return name
                    if models:
                        return models[0]["name"]
                    return "qwen3.5:0.8b"
        except Exception:
            return None
            
    model_name = await asyncio.to_thread(get_model)
    if not model_name:
        return None
        
    from insights import load_history
    history = load_history()
    stats = get_personalized_stats_summary(history)
    report = generate_report()
    
    history_summary = (
        "USER POSTURE & ERGONOMIC TELEMETRY STATS:\n"
        f"- Total Tracking Logs: {stats['total_entries']}\n"
        f"- Average Posture Score: {stats['avg_score']}%\n"
        f"- Slouching Rate: {stats['slouch_pct']}%\n"
        f"- Forward Head Posture (FHP) Rate: {stats['fhp_pct']}%\n"
        f"- Shoulder Asymmetry Rate: {stats['asymmetry_pct']}%\n"
    )
    if stats['avg_screen_dist'] is not None:
        history_summary += f"- Average Screen Distance: {stats['avg_screen_dist']} cm\n"
    if stats['avg_ambient_light'] is not None:
        history_summary += f"- Average Ambient Light: {stats['avg_ambient_light']} level\n"
    if stats['avg_concentration'] is not None:
        history_summary += f"- Average Concentration Index: {stats['avg_concentration']}/100\n"
    if stats['primary_violation'] != "None":
        history_summary += f"- Primary Issue Detected: {stats['primary_violation']}\n"
        
    if report.get("status") == "calibrated" and report.get("recommendations"):
        history_summary += "- Key Insights:\n"
        for rec in report.get("recommendations", []):
            history_summary += f"  * {rec}\n"
            
    live_state = ""
    if last_active_metrics.get("timestamp"):
        time_diff = time.time() - last_active_metrics["timestamp"]
        if time_diff < 60.0:
            live_state = (
                "CURRENT ACTIVE MONITORING STATE (Live Session Active):\n"
                f"- Current Posture Score: {last_active_metrics.get('score', 0):.1f}%\n"
                f"- Active Violations: "
            )
            cur_violations = []
            if last_active_metrics.get("slouching"):
                cur_violations.append("slouching")
            if last_active_metrics.get("fhp"):
                cur_violations.append("forward head tilt (FHP)")
            if last_active_metrics.get("asymmetry"):
                cur_violations.append("shoulder asymmetry")
                
            if cur_violations:
                live_state += f"{', '.join(cur_violations)} (⚠️ User is currently misaligned)\n"
            else:
                live_state += "None (User is sitting in perfect alignment!)\n"
                
            if last_active_metrics.get("screen_distance") is not None:
                live_state += f"- Current Screen Distance: {last_active_metrics['screen_distance']} cm\n"
            if last_active_metrics.get("ambient_brightness") is not None:
                live_state += f"- Current Ambient Light: {last_active_metrics['ambient_brightness']}\n"
            if last_active_metrics.get("concentration_index") is not None:
                live_state += f"- Current Concentration Index: {last_active_metrics['concentration_index']}/100\n"

    system_prompt = (
        "You are ErgoLearn AI, a helpful, highly personalized, and premium desktop ergonomic coach.\n"
        "You analyze the user's real-time biometric and telemetry logs to give precise, actionable posture and eye strain advice.\n\n"
        "IMPORTANT INSTRUCTIONS:\n"
        "- Directly answer the user's question. Do not ignore their query or give a generic copy-pasted report unless they specifically ask for a summary.\n"
        "- Address the user's specific concern (e.g. if they ask for a neck stretch, provide specific neck stretches; if they ask about their screen distance, discuss screen distance).\n"
        "- Dynamically weave in the provided telemetry statistics and current active state in your explanations where relevant, pointing out specific metrics (e.g. slouching percentages) if they query about their performance.\n"
        "- Keep your replies concise, friendly, encouraging, and structured in clean Markdown.\n"
        "- Do not mention that you are a language model or refer to system prompts. Address them conversationally as their coach.\n\n"
        f"{history_summary}\n"
        f"{live_state}"
    )
    
    def post_chat():
        url = "http://localhost:11434/api/chat"
        data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "stream": False
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=8.0) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data["message"]["content"]
        except Exception as e:
            logger.error(f"Failed to fetch response from Ollama: {e}")
            return None
            
    return await asyncio.to_thread(post_chat)

def check_model_present(model_name: str) -> bool:
    import urllib.request
    import json
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get("models", [])
                for m in models:
                    if model_name in m.get("name", ""):
                        return True
    except Exception:
        pass
    return False

async def pull_ollama_model(websocket, model_name: str):
    import urllib.request
    import json
    import asyncio
    
    url = "http://localhost:11434/api/pull"
    data = {"name": model_name, "stream": True}
    
    def run_pull():
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=300.0) as response:
                for line in response:
                    if line:
                        yield line.decode('utf-8').strip()
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            yield json.dumps({"status": "error", "message": str(e)})

    try:
        generator = run_pull()
        loop = asyncio.get_event_loop()
        
        while True:
            line = await loop.run_in_executor(None, next, generator, None)
            if line is None:
                break
                
            try:
                chunk = json.loads(line)
                if chunk.get("status") == "error":
                    await websocket.send(json.dumps({
                        "type": "coach_status",
                        "status": "error",
                        "message": f"Download failed: {chunk.get('message')}"
                    }))
                    return
                    
                status = chunk.get("status", "")
                completed = chunk.get("completed", 0)
                total = chunk.get("total", 0)
                
                percent = 0
                if total > 0:
                    percent = int((completed / total) * 100)
                    msg = f"Downloading AI Model... {percent}%"
                else:
                    msg = status if status else "Initializing..."
                    
                await websocket.send(json.dumps({
                    "type": "coach_status",
                    "status": "downloading",
                    "progress": percent,
                    "message": msg
                }))
            except StopIteration:
                break
            except Exception as e:
                logger.error(f"Error parsing pull chunk: {e}")
                
        await websocket.send(json.dumps({
            "type": "coach_status",
            "status": "ready",
            "message": "AI Coach initialized and ready!"
        }))
        logger.info(f"Model {model_name} pulled successfully.")
    except Exception as e:
        logger.error(f"Failed to pull model: {e}")
        await websocket.send(json.dumps({
            "type": "coach_status",
            "status": "error",
            "message": f"Failed to initialize AI Coach: {e}"
        }))

async def handle_client(websocket):
    global is_monitoring, calibration_countdown, calibration_ipds
    logger.info("Client connected to socket.")
    
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "start":
                if not is_monitoring:
                    is_monitoring = True
                    asyncio.create_task(monitoring_loop(websocket))
                    await websocket.send(json.dumps({"type": "info", "message": "Monitoring started."}))
                else:
                    await websocket.send(json.dumps({"type": "info", "message": "Already monitoring."}))
                    
            elif action == "stop":
                is_monitoring = False
                await websocket.send(json.dumps({"type": "info", "message": "Monitoring stopped."}))
                
            elif action == "calibrate":
                logger.info("Initiating 3-second calibration...")
                calibration_countdown = 6  # 6 half-seconds = 3 seconds
                calibration_ipds = []
                await websocket.send(json.dumps({"type": "info", "message": "Calibrating baseline..."}))
                
            elif action == "get_insights":
                logger.info("Generating Weekly Ergonomics report...")
                report = generate_report()
                await websocket.send(json.dumps({
                    "type": "insights_report",
                    "report": report
                }))
                
            elif action == "check_coach_status":
                logger.info("Checking AI Coach status...")
                model_to_use = "qwen3.5:0.8b"
                
                def is_ollama_online():
                    import urllib.request
                    try:
                        with urllib.request.urlopen("http://localhost:11434/", timeout=1.0) as r:
                            return r.status == 200
                    except Exception:
                        return False

                ollama_running = await asyncio.to_thread(is_ollama_online)
                
                if not ollama_running:
                    logger.info("Ollama is offline. Attempting to start Ollama daemon...")
                    try:
                        import subprocess
                        # Spawn 'ollama serve' in background
                        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        # Poll for up to 3 seconds for Ollama to come online
                        for _ in range(6):
                            await asyncio.sleep(0.5)
                            ollama_running = await asyncio.to_thread(is_ollama_online)
                            if ollama_running:
                                logger.info("Ollama service started successfully.")
                                break
                    except Exception as e:
                        logger.warning(f"Could not automatically launch Ollama serve: {e}")
                
                if not ollama_running:
                    await websocket.send(json.dumps({
                        "type": "coach_status",
                        "status": "offline",
                        "message": "Ollama Offline. Please install and start Ollama locally on port 11434."
                    }))
                else:
                    present = check_model_present(model_to_use)
                    if present:
                        await websocket.send(json.dumps({
                            "type": "coach_status",
                            "status": "ready"
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "coach_status",
                            "status": "initializing",
                            "message": f"Initializing... Model {model_to_use} not found. Starting download..."
                        }))
                        asyncio.create_task(pull_ollama_model(websocket, model_to_use))
                
            elif action == "chat":
                user_message = data.get("message", "")
                logger.info(f"Received chat message: {user_message}")
                response_content = await query_local_ollama(user_message)
                if not response_content:
                    logger.info("Ollama offline or model unavailable. Using local rule-based advisor fallback.")
                    response_content = generate_local_ai_response(user_message, active_metrics=last_active_metrics)
                
                await websocket.send(json.dumps({
                    "type": "chat_response",
                    "message": response_content
                }))
                
            elif action == "seed_mock_data":
                logger.info("Seeding mock telemetry data for demo...")
                try:
                    from seed_data import seed
                    await asyncio.to_thread(seed)
                    await websocket.send(json.dumps({
                        "type": "info",
                        "message": "Demo database successfully seeded for the 7-day Weekly Analysis report!"
                    }))
                except Exception as e:
                    logger.error(f"Failed to seed data: {e}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": f"Failed to seed data: {e}"
                    }))
                    
            else:
                await websocket.send(json.dumps({"type": "error", "message": f"Unknown action: {action}"}))
                
    except Exception as e:
        logger.warning(f"Connection error or client disconnected: {e}")
    finally:
        is_monitoring = False

async def main():
    port = 8765
    logger.info(f"Starting WebSocket sidecar server on ws://localhost:{port}")
    async with serve(handle_client, "localhost", port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server terminated by user.")
