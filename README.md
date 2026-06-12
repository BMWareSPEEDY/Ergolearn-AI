# ErgoLearn AI

### A Privacy-First, Edge-Computing Biomechanical Companion for Healthy Study & Coding Sessions

ErgoLearn AI turns your standard 2D laptop webcam into a real-time, privacy-first posture sensor and workspace wellness coach. Running 100% offline, it strips away raw camera pixels immediately and projects a clean, non-glaring 3D skeletal wireframe onto a canvas, giving you deep wellness insights without sacrificing your privacy or melting your laptop's CPU.

---

## Inspiration

As a student and software developer, I spend upwards of 8 to 10 hours a day glued to my laptop screen, hunched over lines of code and technical text. Over time, I noticed recurring shoulder fatigue, a stiff neck, and a massive drop in my mental focus during long study blocks. 

When I looked at existing posture tracking apps on the market, I realized they all shared the same major flaws: they were either massive resource hogs that drained laptop batteries, or they required streaming raw webcam feeds to external cloud servers. For a workspace utility, that felt like an unnecessary privacy violation. I wanted to build a solution that treated my camera as a fully localized, private biomechanical sensor—giving me deep workspace wellness insights without sacrificing my data or melting my computer's CPU.

---

## What It Does

ErgoLearn AI operates completely offline, turning your webcam into a private sensor suite:
* **Matte Obsidian Skeletal Canvas:** Strips and deletes raw video immediately, showing only a clean, minimal 3D wireframe.
* **Biomechanical Pipeline:** Tracks vertical spine compression (slouching), shoulder plane alignment errors (lateral asymmetry), and calculates your exact screen distance in centimeters using real-time interpupillary distance mapping.
* **Concentration Index:** A responsive 10-second rolling sparkline chart tracking your focus and posture stability.
* **AI Coach Panel:** An interactive workspace wellness companion that reads session logs from `posture_history.json` and provides contextual stretch recommendations (running locally on Ollama, with a built-in offline NLP fallback).

---

## How It's Built

I designed ErgoLearn AI with a lightweight, decoupled multi-process architecture to keep the footprint as tiny as possible.

### The Stack:
* **The Frontend Interface:** Built using HTML5, CSS3, and vanilla JavaScript styled with a flat, sophisticated matte slate and ink aesthetic. I wrapped the interface using **Tauri**, which compiles directly into the operating system's native web rendering engines (WebKit on macOS / WebView2 on Windows) instead of bundling a heavy browser core like Electron does. This keeps the frontend shell framework under a tiny 20 MB container footprint.
* **The AI Sidecar Backend:** A local background Python process managed natively by Tauri that ingests local hardware camera frames and passes them through an optimized MediaPipe skeletal pipeline.
* **The IPC Bridge:** The frontend interface and Python backend communicate locally via a high-speed, secure loopback WebSocket connection (`ws://localhost:8765`) running at up to 30 frames per second.

### Anatomical Invariant Geometry
To make sure sitting closer or further away from the lens doesn't break our tracking, calculations scale dynamically using vector ratios:

---

## Challenges Along the Way

Building a multi-language app that spans JavaScript, Rust, and Python brought up some real engineering hurdles:
1. **The Tab-Throttling Lag:** Early on, when I switched away from the app to type code in another window, the OS would automatically throttle the background frontend JavaScript animation loops. The WebSocket packets from the Python backend would back up in the network buffer. Switching back to the app triggered a crazy, fast-forward "replay" lag. I solved this by stamping millisecond UTC timestamps on the backend data packets, forcing the frontend to immediately drop any frame older than 200ms upon waking up.
2. **Notification Fatigue:** Posture apps can get incredibly annoying if they trigger alerts too quickly. If a developer leans forward for a single second to analyze a complex line of code, they don't want a loud alarm. I had to design a custom **Hysteresis state machine** with a 30-second continuous failure buffer and a strict 60-second cooldown timer so the app remains a silent, helpful companion rather than a constant desktop distraction.
3. **Hardware Constraints:** I initially intended to track eye blinking using Eye Aspect Ratio (EAR) maps to prevent dry eyes, but real-world testing proved that standard laptop webcams at normal screen distances 50 -70 cm are simply too low-resolution for reliable blink data. Rather than shipping a glitchy feature, I made the engineering call to strip out the blink code entirely and focus heavily on rock-solid 3D skeletal posture layout tracking.

---

## Wins & Proud Moments

* **Depth Without Depth Sensors:** Implementing the pinhole camera approximation formula using the pixel delta between landmarks 468 and 473 (the center of human irises) allowed us to calculate absolute screen proximity in centimeters without forcing the user to own expensive depth cameras or LiDAR hardware.
* **Ultra-Responsive Focus Tracker:** Re-engineering our Concentration Index from a sluggish 60-second moving average down to a responsive 10-second window means the data visualization reacts to sudden fatigue drops smoothly and dynamically in under two seconds.
* **100% Privacy-First:** Building a cross-platform machine learning app that values user privacy above everything else.

---

## What I Learned

This project completely shifted how I approach systems architecture. It taught me that building software with AI components doesn't mean you have to plug everything into expensive, cloud-hosted API endpoints that compromise user data. By leveraging highly optimized edge frameworks, local WebSockets, and on-device logic routines, you can build incredibly robust, low-latency, and highly secure software that runs completely on your own machine.

---

## What's Next for ErgoLearn

The immediate next step for ErgoLearn AI is expanding our conversational ecosystem. Our current AI Coach features a dual-tiered architecture that targets a local **Ollama** instance (running an optimized, quantized LLM model) or falls back to an offline rule-based NLP parser that reads the local `posture_history.json` logs when Ollama is closed. I want to build out custom, interactive desktop stretch routines where the neon 3D skeleton actively guides the user through shoulder rolls and cervical stretches, updating the UI in real-time as they complete each physical movement correctly.

---

## Setting Up & Running Locally

### Prerequisites
* **Node.js** (v18+) & **npm**
* **Python** (v3.10+)
* **Rust & Cargo** (Required to compile the Tauri bundle)

### Step-by-Step Setup
1. **Clone the repository and install frontend dependencies:**
   ```bash
   npm install
   ```
2. **Setup the Python virtual environment and install dependencies:**
   ```bash
   cd src-python
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd ..
   ```

### Running the App
We have two handy scripts to get you up and running depending on your development workflow:

#### Option A: Run the Desktop Client (Tauri + Python sidecar)
Use the [full-run](file:///Users/ashishpaliwal/apps/ErgoLearn%20AI/full-run) script:
```bash
./full-run
```

#### Option B: Run in the Browser (Vite + Python server)
Use the [test-run](file:///Users/ashishpaliwal/apps/ErgoLearn%20AI/test-run) script:
```bash
./test-run
```
---

## Project Structure

* **[src-frontend](file:///Users/ashishpaliwal/apps/ErgoLearn%20AI/src-frontend)** - Web dashboard & 3D canvas (HTML/CSS/JS)
* **[src-python](file:///Users/ashishpaliwal/apps/ErgoLearn%20AI/src-python)** - Local MediaPipe & WebSocket backend
* **[src-tauri](file:///Users/ashishpaliwal/apps/ErgoLearn%20AI/src-tauri)** - Native desktop wrapper configuration
* **[full-run](file:///Users/ashishpaliwal/apps/ErgoLearn%20AI/full-run)** - Start Tauri app
* **[test-run](file:///Users/ashishpaliwal/apps/ErgoLearn%20AI/test-run)** - Start web client in default browser
