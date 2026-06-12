// --- DOM Elements ---
const connectionDot = document.getElementById('connection-dot');
const connectionStatus = document.getElementById('connection-status');
const liveBadge = document.getElementById('live-badge');
const canvas = document.getElementById('pose-canvas');
const ctx = canvas.getContext('2d');
const canvasPlaceholder = document.getElementById('canvas-placeholder');
const calibrationOverlay = document.getElementById('calibration-overlay');
const calibrationCounter = document.getElementById('calibration-counter');

// Score Elements
const scoreNumber = document.getElementById('score-number');
const scoreGaugeFill = document.getElementById('score-gauge-fill');
const ratingBadge = document.getElementById('rating-badge');
const ratingDesc = document.getElementById('rating-desc');

// Diagnostics
const diagSlouch = document.getElementById('diag-slouch');
const valSlouch = document.getElementById('val-slouch');
const fillSlouch = document.getElementById('fill-slouch');

const diagFhp = document.getElementById('diag-fhp');
const valFhp = document.getElementById('val-fhp');
const fillFhp = document.getElementById('fill-fhp');

const diagAsymmetry = document.getElementById('diag-asymmetry');
const valAsymmetry = document.getElementById('val-asymmetry');
const fillAsymmetry = document.getElementById('fill-asymmetry');

// Controls & Stats
const btnToggleMonitor = document.getElementById('btn-toggle-monitor');
const btnCalibrate = document.getElementById('btn-calibrate');
const statTime = document.getElementById('stat-time');
const statViolations = document.getElementById('stat-violations');

// Tab Navigation Elements
const tabLive = document.getElementById('tab-live');
const tabInsights = document.getElementById('tab-insights');
const contentLive = document.getElementById('content-live');
const contentInsights = document.getElementById('content-insights');
const viewTitle = document.getElementById('view-title');

// Mini View Layout Elements
const btnMiniMode = document.getElementById('btn-mini-mode');
const btnExpandMode = document.getElementById('btn-expand-mode');
const miniScoreNumber = document.getElementById('mini-score-number');
const miniStatTime = document.getElementById('mini-stat-time');
const miniStatusDot = document.getElementById('mini-status-dot');
const miniWidgetLayout = document.getElementById('mini-widget-layout');

// Eye & Ambient Health DOM Elements
const concentrationGraphContainer = document.getElementById('concentration-graph-container');
const concentrationCanvas = document.getElementById('concentration-canvas');
const valConcentrationIndex = document.getElementById('val-concentration-index');

const valAmbientLight = document.getElementById('val-ambient-light');
const lblAmbientStatus = document.getElementById('lbl-ambient-status');
const ambientDarkTip = document.getElementById('ambient-dark-tip');

// Shimmer Loader Elements
const shimmerSlouch = document.getElementById('shimmer-slouch');
const shimmerFhp = document.getElementById('shimmer-fhp');
const shimmerAsymmetry = document.getElementById('shimmer-asymmetry');

// Insights Dashboard Elements
const aiRecsContainer = document.getElementById('ai-recs-container');
const insightFocusTime = document.getElementById('insight-focus-time');
const insightHealthyTime = document.getElementById('insight-healthy-time');
const hourlyChartContainer = document.getElementById('hourly-chart-container');
const dailyChartContainer = document.getElementById('daily-chart-container');

// Screen Distance DOM Elements
const valScreenDistance = document.getElementById('val-screen-distance');
const lblDistanceStatus = document.getElementById('lbl-distance-status');
const distanceRiskIndicator = document.getElementById('distance-risk-indicator');

// AI Coach DOM Elements
const tabCoach = document.getElementById('tab-coach');
const contentCoach = document.getElementById('content-coach');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatForm = document.getElementById('chat-form');
const btnSend = document.getElementById('btn-send');
const chatStatusBadge = document.getElementById('chat-status-badge');
const coachBridgeVal = document.getElementById('coach-bridge-val');
const coachOllamaVal = document.getElementById('coach-ollama-val');
const coachActiveSessionVal = document.getElementById('coach-active-session-val');
const coachLogsVal = document.getElementById('coach-logs-val');
const coachInitOverlay = document.getElementById('coach-init-overlay');
const coachInitTitle = document.getElementById('coach-init-title');
const coachInitMsg = document.getElementById('coach-init-msg');
const coachInitProgressFill = document.getElementById('coach-init-progress-fill');
const btnBypassInit = document.getElementById('btn-bypass-init');

// --- State Variables ---
let chartTooltip = null;
let socket = null;
let isConnected = false;
let isMonitoring = false;
let isSimulationMode = false;
let sessionStartTime = null;
let sessionTimerInterval = null;
let poorPostureStartTime = null;
let warningStartTime = null;
let criticalStartTime = null;
let violationCount = 0;
let concentrationHistory = [];
let darkEnvironmentStartTime = null;
let closeDistanceStartTime = null;
let lastDistanceAlertTime = 0;
const GAUGE_CIRCUMFERENCE = 264; // 2 * pi * r (2 * 3.14159 * 42)

// --- Local Simulation variables ---
let simulationInterval = null;
let simTime = 0;
let mockCalibrationActive = false;
let mockCalibrationCountdown = 0;

// Baseline values for simulation analysis (JS-side mirror of Python Biomechanics)
let simBaseline = {
  slouchDelta: 0.25,
  fhpRatio: 0.33,
  shoulderWidth: 0.30,
  calibrated: false
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  connectWebSocket();
  setupEventListeners();
  requestNotificationPermission();
});

// --- WebSocket Connection ---
function connectWebSocket() {
  updateConnectionStatus(false, 'Connecting...');
  
  socket = new WebSocket('ws://localhost:8765');
  
  socket.onopen = () => {
    isConnected = true;
    isSimulationMode = false;
    updateConnectionStatus(true, 'Connected');
    btnToggleMonitor.disabled = false;
    btnCalibrate.disabled = false;
  };
  
  socket.onclose = () => {
    isConnected = false;
    updateConnectionStatus(false, 'Disconnected (Running Demo Mode)');
    // If we disconnect during active monitoring, switch to simulation mode
    if (isMonitoring && !isSimulationMode) {
      switchToSimulation();
    }
    
    // In demo mode, buttons are always enabled
    btnToggleMonitor.disabled = false;
    btnCalibrate.disabled = false;
    
    // Auto-try to reconnect in the background
    setTimeout(connectWebSocket, 5000);
  };
  
  socket.onerror = (error) => {
    // Suppress console spam when server isn't running
  };
  
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleServerMessage(data);
  };
}

function updateConnectionStatus(connected, text) {
  if (connected) {
    connectionDot.className = 'status-dot connected';
    connectionStatus.textContent = text;
    if (coachBridgeVal) {
      coachBridgeVal.textContent = 'Active';
      coachBridgeVal.className = 'c-stat-val text-success';
    }
  } else {
    connectionDot.className = 'status-dot disconnected';
    connectionStatus.textContent = text;
    if (coachBridgeVal) {
      coachBridgeVal.textContent = 'Offline';
      coachBridgeVal.className = 'c-stat-val text-danger';
    }
    if (coachOllamaVal) {
      coachOllamaVal.textContent = 'Offline';
      coachOllamaVal.className = 'c-stat-val text-danger';
    }
  }
}

function bypassInitialization() {
  if (coachInitOverlay && !coachInitOverlay.classList.contains('hidden')) {
    coachInitOverlay.classList.add('hidden');
    chatInput.disabled = false;
    btnSend.disabled = false;
    
    // Update badge and sidebar to fallback state if not already ready
    if (chatStatusBadge.textContent !== 'Ollama AI (Ready)') {
      chatStatusBadge.textContent = 'Offline Fallback';
      chatStatusBadge.style.color = 'var(--color-warning)';
      chatStatusBadge.style.borderColor = 'rgba(255, 179, 0, 0.25)';
      chatStatusBadge.style.background = 'rgba(255, 179, 0, 0.08)';
      
      if (coachOllamaVal) {
        coachOllamaVal.textContent = 'Bypassed (Fallback)';
        coachOllamaVal.className = 'c-stat-val text-warning';
      }
      
      appendChatMessage('system', 'Bypassed local AI engine initialization. Operating in offline local NLP fallback mode.');
    }
  }
}

// --- Event Listeners ---
function setupEventListeners() {
  btnToggleMonitor.addEventListener('click', () => {
    // Request permission on click (user gesture) to ensure notifications are allowed
    requestNotificationPermission();
    if (isMonitoring) {
      if (isSimulationMode) {
        handleStopMonitoring();
      } else {
        sendSocketAction('stop');
        handleStopMonitoring();
      }
    } else {
      if (socket && socket.readyState === WebSocket.OPEN) {
        sendSocketAction('start');
        handleStartMonitoring(false);
      } else {
        switchToSimulation();
      }
    }
  });

  btnCalibrate.addEventListener('click', () => {
    // Request permission on click (user gesture) to ensure notifications are allowed
    requestNotificationPermission();
    if (isSimulationMode) {
      startMockCalibration();
    } else {
      sendSocketAction('calibrate');
    }
  });

  // Tab switcher listeners
  tabLive.addEventListener('click', () => switchTab('live'));
  tabInsights.addEventListener('click', () => switchTab('insights'));
  tabCoach.addEventListener('click', () => switchTab('coach'));

  // Chat submit event
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      handleSendChatMessage();
    });
  }

  // Bypass initialization overlay
  if (btnBypassInit) {
    btnBypassInit.addEventListener('click', () => {
      bypassInitialization();
    });
  }

  // Quick prompt chips
  const promptChips = document.querySelectorAll('.prompt-chip');
  promptChips.forEach(chip => {
    chip.addEventListener('click', (e) => {
      e.preventDefault();
      console.log('Prompt chip clicked:', chip.getAttribute('data-prompt'));
      const promptText = chip.getAttribute('data-prompt');
      if (promptText && chatInput) {
        bypassInitialization(); // Ensure chat window is visible and enabled
        chatInput.value = promptText;
        handleSendChatMessage();
      }
    });
  });

  // Seeding demo data listener
  const btnSeedData = document.getElementById('btn-seed-data');
  if (btnSeedData) {
    btnSeedData.addEventListener('click', () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        btnSeedData.disabled = true;
        btnSeedData.textContent = 'Seeding...';
        sendSocketAction('seed_mock_data');
      } else {
        alert('Cannot seed: Backend WebSocket disconnected.');
      }
    });
  }

  // Concentration sparkline interactivity
  if (concentrationCanvas) {
    concentrationCanvas.addEventListener('mousemove', (e) => {
      const values = concentrationCanvas.values;
      if (!values || values.length < 2) return;
      
      const rect = concentrationCanvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      
      const maxPoints = 50;
      const step = rect.width / (maxPoints - 1);
      
      // Calculate index corresponding to mouseX
      const width = rect.width;
      const idx = Math.round(values.length - 1 - (width - mouseX) / step);
      
      if (idx >= 0 && idx < values.length) {
        const val = values[idx];
        showTooltip(e, `Concentration Index (Recent Point)`, Math.round(val));
      } else {
        hideTooltip();
      }
    });
    
    concentrationCanvas.addEventListener('mouseleave', () => {
      hideTooltip();
    });
  }
  // Mini View Toggles
  btnMiniMode.addEventListener('click', () => toggleMiniMode(true));
  btnExpandMode.addEventListener('click', () => toggleMiniMode(false));

  // Enable dragging on mini-mode widget
  if (miniWidgetLayout) {
    miniWidgetLayout.addEventListener('mousedown', (e) => {
      // Don't drag if clicking buttons inside the widget (like btnExpandMode)
      if (e.target.closest('#btn-expand-mode')) return;
      
      if (window.__TAURI__ && window.__TAURI__.window) {
        window.__TAURI__.window.getCurrentWindow().startDragging().catch((err) => {
          console.error('Failed to start window drag:', err);
        });
      }
    });
  }
}

function switchTab(tab) {
  // Remove active from all tabs
  tabLive.classList.remove('active');
  tabInsights.classList.remove('active');
  tabCoach.classList.remove('active');
  
  // Hide all panels
  contentLive.classList.add('hidden');
  contentInsights.classList.add('hidden');
  contentCoach.classList.add('hidden');
  
  if (tab === 'live') {
    tabLive.classList.add('active');
    contentLive.classList.remove('hidden');
    viewTitle.textContent = 'Dashboard';
  } else if (tab === 'insights') {
    tabInsights.classList.add('active');
    contentInsights.classList.remove('hidden');
    viewTitle.textContent = 'Ergo Insights';
    fetchInsights();
  } else if (tab === 'coach') {
    tabCoach.classList.add('active');
    contentCoach.classList.remove('hidden');
    viewTitle.textContent = 'AI Ergonomic Coach';
    
    // Trigger WebSocket status check
    if (socket && socket.readyState === WebSocket.OPEN) {
      // Set status to initializing while waiting for sidecar response
      if (coachInitOverlay) {
        coachInitOverlay.classList.remove('hidden');
        coachInitTitle.textContent = 'Initializing AI Engine...';
        coachInitMsg.textContent = 'Connecting to local LLM daemon (qwen3.5:0.8b)...';
        coachInitProgressFill.style.width = '0%';
      }
      chatInput.disabled = true;
      btnSend.disabled = true;
      
      if (coachOllamaVal) {
        coachOllamaVal.textContent = 'Connecting...';
        coachOllamaVal.className = 'c-stat-val text-warning';
      }
      
      // Send the status check action
      socket.send(JSON.stringify({ action: 'check_coach_status' }));
    } else {
      // Offline fallback if WebSocket is offline entirely
      if (coachInitOverlay) {
        coachInitOverlay.classList.add('hidden');
      }
      chatInput.disabled = false;
      btnSend.disabled = false;
      chatStatusBadge.textContent = 'Offline Fallback';
      chatStatusBadge.style.color = 'var(--color-warning)';
      chatStatusBadge.style.borderColor = 'rgba(255, 179, 0, 0.25)';
      chatStatusBadge.style.background = 'rgba(255, 179, 0, 0.08)';
      
      if (coachOllamaVal) {
        coachOllamaVal.textContent = 'Offline';
        coachOllamaVal.className = 'c-stat-val text-danger';
      }
    }
  }
}

async function toggleMiniMode(enable) {
  if (enable) {
    document.body.classList.add('mini-mode');
    if (window.__TAURI__ && window.__TAURI__.window) {
      try {
        const appWindow = window.__TAURI__.window.getCurrentWindow();
        await appWindow.setDecorations(false);
        await appWindow.setAlwaysOnTop(true);
        const size = window.__TAURI__.window.LogicalSize ? 
          new window.__TAURI__.window.LogicalSize(240, 80) : 
          { type: 'Logical', width: 240, height: 80 };
        await appWindow.setSize(size);
      } catch (e) {
        console.error('Tauri window resize failed:', e);
      }
    }
  } else {
    document.body.classList.remove('mini-mode');
    document.body.classList.remove('warning-pulse');
    document.body.classList.remove('critical-pulse');
    if (window.__TAURI__ && window.__TAURI__.window) {
      try {
        const appWindow = window.__TAURI__.window.getCurrentWindow();
        await appWindow.setDecorations(true);
        await appWindow.setAlwaysOnTop(false);
        const size = window.__TAURI__.window.LogicalSize ? 
          new window.__TAURI__.window.LogicalSize(1100, 750) : 
          { type: 'Logical', width: 1100, height: 750 };
        await appWindow.setSize(size);
      } catch (e) {
        console.error('Tauri window restore failed:', e);
      }
    }
  }
}

function fetchInsights() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    sendSocketAction('get_insights');
  } else {
    // Render offline/simulation mock insights report
    const mockReport = generateMockInsightsReport();
    renderInsights(mockReport);
  }
}

function sendSocketAction(action) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action }));
  }
}

// --- Monitoring Handlers ---
function handleStartMonitoring(demo = false) {
  isMonitoring = true;
  isSimulationMode = demo;
  
  liveBadge.className = 'live-badge active';
  liveBadge.textContent = demo ? 'LIVE (DEMO)' : 'LIVE';
  
  btnToggleMonitor.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="4" y="4" width="16" height="16"></rect>
    </svg>
    Stop Monitoring
  `;
  canvasPlaceholder.classList.add('hidden');
  
  if (coachActiveSessionVal) {
    coachActiveSessionVal.textContent = demo ? 'Active (Demo)' : 'Active (Tracking)';
    coachActiveSessionVal.className = 'c-stat-val text-success';
  }
  
  // Start session clock
  sessionStartTime = Date.now();
  sessionTimerInterval = setInterval(updateSessionTime, 1000);
}

function handleStopMonitoring() {
  isMonitoring = false;
  isSimulationMode = false;
  mockCalibrationActive = false;
  
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
  }
  
  if (coachActiveSessionVal) {
    coachActiveSessionVal.textContent = 'Offline';
    coachActiveSessionVal.className = 'c-stat-val';
  }
  
  liveBadge.className = 'live-badge';
  liveBadge.textContent = 'OFFLINE';
  btnToggleMonitor.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>
    Start Monitoring
  `;
  canvasPlaceholder.classList.remove('hidden');
  calibrationOverlay.classList.add('hidden');
  clearCanvas();
  
  // Stop session clock
  clearInterval(sessionTimerInterval);
  sessionStartTime = null;
  poorPostureStartTime = null;
  warningStartTime = null;
  criticalStartTime = null;
  resetScoresAndDiagnostics();
}

function updateSessionTime() {
  if (!sessionStartTime) return;
  const elapsedMs = Date.now() - sessionStartTime;
  const elapsedSecs = Math.floor(elapsedMs / 1000);
  const mins = Math.floor(elapsedSecs / 60).toString().padStart(2, '0');
  const secs = (elapsedSecs % 60).toString().padStart(2, '0');
  const displayTime = `${mins}:${secs}`;
  statTime.textContent = displayTime;
  miniStatTime.textContent = displayTime;
}

// --- Reset UI ---
function resetScoresAndDiagnostics() {
  scoreNumber.textContent = '--';
  miniScoreNumber.textContent = '--';
  updateGauge(0);
  ratingBadge.className = 'rating-badge';
  ratingBadge.textContent = 'Ready';
  ratingDesc.textContent = 'Calibrate to begin tracking posture quality.';
  
  miniStatusDot.className = 'mini-status-dot disconnected';
  document.body.classList.remove('warning-pulse');
  document.body.classList.remove('critical-pulse');
  
  valSlouch.textContent = '--';
  fillSlouch.style.width = '0%';
  diagSlouch.className = 'diagnostic-item';
  shimmerSlouch.classList.remove('hidden');
  
  valFhp.textContent = '--';
  fillFhp.style.width = '0%';
  diagFhp.className = 'diagnostic-item';
  shimmerFhp.classList.remove('hidden');
  
  valAsymmetry.textContent = '--';
  fillAsymmetry.style.width = '0%';
  diagAsymmetry.className = 'diagnostic-item';
  shimmerAsymmetry.classList.remove('hidden');

  // Reset Eye & Ambient Health UI & States

  
  valScreenDistance.textContent = '--';
  valScreenDistance.className = 'eye-stat-val';
  lblDistanceStatus.textContent = '(Inactive)';
  lblDistanceStatus.className = 'eye-stat-status';
  distanceRiskIndicator.classList.add('hidden');
  
  valAmbientLight.textContent = '--';
  valAmbientLight.classList.remove('warning');
  lblAmbientStatus.textContent = '(Inactive)';
  lblAmbientStatus.className = 'eye-stat-status';
  ambientDarkTip.classList.add('hidden');
  
  valConcentrationIndex.textContent = '--%';
  // Keep concentrationGraphContainer visible as requested
  
  concentrationHistory = [];
  darkEnvironmentStartTime = null;
}

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// --- Server Message Handling ---
function handleServerMessage(data) {
  if (isSimulationMode) return; // Ignore actual messages if we forced demo
  
  // Prevent fast-forward/catch-up video replay when returning from background throttling
  if (data.timestamp && (data.type === 'posture_update' || data.type === 'calibration_progress')) {
    const age = Date.now() - data.timestamp;
    if (age > 200) {
      // Discard stale background frames/updates
      return;
    }
  }
  
  if (data.type === 'calibration_progress') {
    calibrationOverlay.classList.remove('hidden');
    const countSeconds = Math.ceil(data.remaining / 2);
    calibrationCounter.textContent = countSeconds;
    
    drawSkeleton(data.landmarks, false, data.frame);
  } 
  
  else if (data.type === 'calibration_complete') {
    calibrationOverlay.classList.add('hidden');
    ratingBadge.className = 'rating-badge excellent';
    ratingBadge.textContent = 'Calibrated';
    ratingDesc.textContent = 'Monitoring posture against your customized baseline.';
    
    // Hide shimmer loaders
    shimmerSlouch.classList.add('hidden');
    shimmerFhp.classList.add('hidden');
    shimmerAsymmetry.classList.add('hidden');
  } 

  
  else if (data.type === 'posture_update') {
    const landmarks = data.landmarks;
    const analysis = data.analysis;
    const frame = data.frame;
    
    drawSkeleton(landmarks, analysis, frame);
    
    if (analysis.status === 'calibrated') {
      updateUI(analysis);
    }
  }
  
  else if (data.type === 'insights_report') {
    renderInsights(data.report);
  }
  
  else if (data.type === 'chat_response') {
    removeChatTypingIndicator();
    appendChatMessage('assistant', data.message);
  }
  
  else if (data.type === 'coach_status') {
    if (data.status === 'ready') {
      if (coachInitOverlay) {
        coachInitOverlay.classList.add('hidden');
      }
      chatInput.disabled = false;
      btnSend.disabled = false;
      
      // Update UI Status Badge
      chatStatusBadge.textContent = 'Ollama AI (Ready)';
      chatStatusBadge.style.color = 'var(--color-secondary)';
      chatStatusBadge.style.borderColor = 'rgba(0, 230, 118, 0.25)';
      chatStatusBadge.style.background = 'rgba(0, 230, 118, 0.08)';
      
      if (coachOllamaVal) {
        coachOllamaVal.textContent = 'Ready (qwen3.5:0.8b)';
        coachOllamaVal.className = 'c-stat-val text-success';
      }
    }
    
    else if (data.status === 'initializing' || data.status === 'downloading') {
      if (coachInitOverlay) {
        coachInitOverlay.classList.remove('hidden');
        coachInitTitle.textContent = 'Initializing AI Model...';
        coachInitMsg.textContent = data.message || 'Preparing local model files...';
        if (data.progress !== undefined) {
          coachInitProgressFill.style.width = data.progress + '%';
        } else {
          coachInitProgressFill.style.width = '0%';
        }
      }
      chatInput.disabled = true;
      btnSend.disabled = true;
      
      if (coachOllamaVal) {
        coachOllamaVal.textContent = data.status === 'downloading' ? `Downloading (${data.progress}%)` : 'Initializing...';
        coachOllamaVal.className = 'c-stat-val text-warning';
      }
    }
    
    else if (data.status === 'offline') {
      if (coachInitOverlay) {
        coachInitOverlay.classList.add('hidden');
      }
      chatInput.disabled = false;
      btnSend.disabled = false;
      
      chatStatusBadge.textContent = 'Offline Fallback';
      chatStatusBadge.style.color = 'var(--color-warning)';
      chatStatusBadge.style.borderColor = 'rgba(255, 179, 0, 0.25)';
      chatStatusBadge.style.background = 'rgba(255, 179, 0, 0.08)';
      
      if (coachOllamaVal) {
        coachOllamaVal.textContent = 'Offline';
        coachOllamaVal.className = 'c-stat-val text-danger';
      }
      
      appendChatMessage('system', `Ollama is offline: ${data.message}. Operating in offline local NLP fallback mode.`);
    }
    
    else if (data.status === 'error') {
      if (coachInitOverlay) {
        coachInitOverlay.classList.remove('hidden');
        coachInitTitle.textContent = 'Initialization Failed';
        coachInitMsg.textContent = data.message || 'An error occurred during local LLM setup.';
        coachInitProgressFill.style.width = '0%';
      }
      chatInput.disabled = true;
      btnSend.disabled = true;
      
      if (coachOllamaVal) {
        coachOllamaVal.textContent = 'Error';
        coachOllamaVal.className = 'c-stat-val text-danger';
      }
    }
  }
  
  else if (data.type === 'info') {
    const btnSeedData = document.getElementById('btn-seed-data');
    if (btnSeedData) {
      btnSeedData.disabled = false;
      btnSeedData.textContent = 'Seed Demo Data';
    }
    alert(data.message);
    sendSocketAction('get_insights');
  }
  
  else if (data.type === 'error') {
    const btnSeedData = document.getElementById('btn-seed-data');
    if (btnSeedData) {
      btnSeedData.disabled = false;
      btnSeedData.textContent = 'Seed Demo Data';
    }
    alert('Error: ' + data.message);
  }
}

function updateUI(analysis) {
  const metrics = analysis.metrics;
  const violations = analysis.violations;
  
  // Update Score Gauge
  const score = metrics.score;
  scoreNumber.textContent = Math.round(score);
  miniScoreNumber.textContent = Math.round(score); // Sync mini score
  updateGauge(score);
  
  // Sync mini status dot
  if (score >= 85) {
    miniStatusDot.className = 'mini-status-dot green';
  } else if (score >= 60) {
    miniStatusDot.className = 'mini-status-dot amber';
  } else {
    miniStatusDot.className = 'mini-status-dot red';
  }

  // Rating badges & desc
  if (score >= 85) {
    ratingBadge.className = 'rating-badge excellent';
    ratingBadge.textContent = 'Excellent';
    ratingDesc.textContent = 'Great job! Your alignment is solid. Keep it up.';
  } else if (score >= 60) {
    ratingBadge.className = 'rating-badge warning';
    ratingBadge.textContent = 'Warning';
    ratingDesc.textContent = 'Slight posture deflection detected. Straighten up.';
  } else {
    ratingBadge.className = 'rating-badge critical';
    ratingBadge.textContent = 'Violating';
    ratingDesc.textContent = 'Bad ergonomics detected. Reset your seating position.';
  }

  // Update Diagnostics
  // 1. Slouching
  const slouchPercentage = Math.min(100, Math.round(metrics.slouch_ratio * 100));
  valSlouch.textContent = `${slouchPercentage}%`;
  fillSlouch.style.width = `${Math.max(0, Math.min(100, slouchPercentage))}%`;
  diagSlouch.className = violations.slouch ? 'diagnostic-item alert' : 'diagnostic-item';
  
  // 2. FHP
  const fhpDevPct = Math.round((metrics.fhp_deviation - 1) * 100);
  valFhp.textContent = fhpDevPct > 0 ? `+${fhpDevPct}%` : `${fhpDevPct}%`;
  const fhpFill = Math.max(0, Math.min(100, (metrics.fhp_deviation - 1) * 200));
  fillFhp.style.width = `${fhpFill}%`;
  diagFhp.className = violations.forward_head ? 'diagnostic-item alert' : 'diagnostic-item';
  
  // 3. Asymmetry
  const degrees = Math.round(Math.atan(metrics.shoulder_slope) * (180 / Math.PI));
  valAsymmetry.textContent = `${degrees}°`;
  const asymmetryFill = Math.min(100, (Math.abs(metrics.shoulder_slope) / 0.3) * 100);
  fillAsymmetry.style.width = `${asymmetryFill}%`;
  diagAsymmetry.className = violations.lateral_asymmetry ? 'diagnostic-item alert' : 'diagnostic-item';

  // --- Alert Trigger Logic with Hysteresis ---
  if (score >= 85) {
    poorPostureStartTime = null;
    warningStartTime = null;
    criticalStartTime = null;
    document.body.classList.remove('warning-pulse');
    document.body.classList.remove('critical-pulse');
  } else if (score < 60) {
    poorPostureStartTime = null;
    warningStartTime = null;
    if (criticalStartTime === null) {
      criticalStartTime = Date.now();
    }
    const elapsed = (Date.now() - criticalStartTime) / 1000;
    if (elapsed >= 3.0) {
      triggerPostureAlert('Postural Alert - ErgoLearn AI', 'Critical slouching/violation detected! Please sit upright.');
      criticalStartTime = Date.now();
    } else if (elapsed >= 1.0) {
      document.body.classList.add('critical-pulse');
      document.body.classList.remove('warning-pulse');
    } else {
      document.body.classList.remove('warning-pulse');
      document.body.classList.remove('critical-pulse');
    }
  } else {
    // 60 <= score < 85
    poorPostureStartTime = null;
    criticalStartTime = null;
    if (warningStartTime === null) {
      warningStartTime = Date.now();
    }
    const elapsed = (Date.now() - warningStartTime) / 1000;
    if (elapsed >= 30.0) {
      triggerPostureAlert('Warning Posture - ErgoLearn AI', 'Slight posture deflection detected. Straighten up!');
      warningStartTime = Date.now();
    } else if (elapsed >= 5.0) {
      document.body.classList.add('warning-pulse');
      document.body.classList.remove('critical-pulse');
    } else {
      document.body.classList.remove('warning-pulse');
      document.body.classList.remove('critical-pulse');
    }
  }

  // Update Eye & Ambient Health UI
  const ear = metrics.ear;
  const brightness = metrics.ambient_brightness;
  const concentrationIndex = metrics.concentration_index;

  // 2. Ambient Lighting
  if (brightness !== undefined && brightness !== null) {
    valAmbientLight.textContent = Math.round(brightness);
    if (brightness < 40) {
      lblAmbientStatus.textContent = '(Too Dark)';
      lblAmbientStatus.classList.add('warning');
      valAmbientLight.classList.add('warning');
      
      if (darkEnvironmentStartTime === null) {
        darkEnvironmentStartTime = Date.now();
      }
      const elapsedSecs = (Date.now() - darkEnvironmentStartTime) / 1000;
      const tipThreshold = isSimulationMode ? 5.0 : 300.0;
      if (elapsedSecs >= tipThreshold) {
        ambientDarkTip.classList.remove('hidden');
      }
    } else {
      lblAmbientStatus.textContent = '(Healthy)';
      lblAmbientStatus.classList.remove('warning');
      valAmbientLight.classList.remove('warning');
      ambientDarkTip.classList.add('hidden');
      darkEnvironmentStartTime = null;
    }
  }

  // 4. Screen Distance
  const distance = metrics.screen_distance;
  if (distance !== undefined && distance !== null) {
    valScreenDistance.textContent = `${Math.round(distance)} cm`;
    
    if (distance < 50) {
      lblDistanceStatus.textContent = '(Too Close)';
      lblDistanceStatus.className = 'eye-stat-status critical-distance';
      valScreenDistance.className = 'eye-stat-val critical-distance';
      distanceRiskIndicator.classList.remove('hidden');
      
      if (closeDistanceStartTime === null) {
        closeDistanceStartTime = Date.now();
      }
      
      const elapsedDistance = (Date.now() - closeDistanceStartTime) / 1000;
      if (elapsedDistance >= 10.0) {
        const now = Date.now();
        if (now - lastDistanceAlertTime >= 20000) {
          triggerPostureAlert('Ciliary Strain Warning - ErgoLearn AI', 'You are sitting too close to the screen (less than 50 cm) for over 10 seconds. Please sit back!');
          lastDistanceAlertTime = now;
        }
      }
    } else {
      lblDistanceStatus.textContent = '(Healthy)';
      lblDistanceStatus.className = 'eye-stat-status';
      valScreenDistance.className = 'eye-stat-val';
      distanceRiskIndicator.classList.add('hidden');
      closeDistanceStartTime = null;
    }
  } else {
    valScreenDistance.textContent = '-- cm';
    lblDistanceStatus.textContent = '(Calibrate first)';
    lblDistanceStatus.className = 'eye-stat-status';
    valScreenDistance.className = 'eye-stat-val';
    distanceRiskIndicator.classList.add('hidden');
    closeDistanceStartTime = null;
  }

  // 3. Concentration Sparkline
  if (concentrationIndex !== undefined && concentrationIndex !== null) {
    valConcentrationIndex.textContent = `${Math.round(concentrationIndex)}%`;
    concentrationGraphContainer.classList.remove('hidden');
    
    concentrationHistory.push(concentrationIndex);
    if (concentrationHistory.length > 50) {
      concentrationHistory.shift();
    }
    
    drawConcentrationSparkline(concentrationHistory);
  }
}

function drawConcentrationSparkline(values) {
  if (!concentrationCanvas) return;
  concentrationCanvas.values = values;
  const sCtx = concentrationCanvas.getContext('2d');
  
  // Align coordinate grid with CSS bounds to prevent blurry line distortion
  const rect = concentrationCanvas.getBoundingClientRect();
  if (rect.width > 0 && rect.height > 0) {
    if (concentrationCanvas.width !== Math.round(rect.width) || concentrationCanvas.height !== Math.round(rect.height)) {
      concentrationCanvas.width = Math.round(rect.width);
      concentrationCanvas.height = Math.round(rect.height);
    }
  }
  
  const width = concentrationCanvas.width;
  const height = concentrationCanvas.height;
  
  sCtx.clearRect(0, 0, width, height);
  
  if (values.length < 2) return;
  
  // Draw subtle horizontal grid lines
  sCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
  sCtx.lineWidth = 1;
  for (let i = 1; i < 3; i++) {
    const y = (height / 3) * i;
    sCtx.beginPath();
    sCtx.moveTo(0, y);
    sCtx.lineTo(width, y);
    sCtx.stroke();
  }
  
  const maxPoints = 50;
  const step = width / (maxPoints - 1);
  
  // Calculate point coordinates
  const points = [];
  for (let i = 0; i < values.length; i++) {
    // Newest points are drawn on the right, shifting older points left
    const x = width - (values.length - 1 - i) * step;
    // Map score (0-100) to canvas height (leaving 3px padding top/bottom)
    const y = height - (values[i] / 100.0) * (height - 6) - 3;
    points.push({ x, y });
  }
  
  // Draw the off-white line
  sCtx.beginPath();
  sCtx.lineWidth = 1.5;
  sCtx.strokeStyle = '#f4f4f6';
  
  sCtx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    sCtx.lineTo(points[i].x, points[i].y);
  }
  sCtx.stroke();
  
  // Fill gradient area below the line
  sCtx.beginPath();
  sCtx.moveTo(points[0].x, height);
  sCtx.lineTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    sCtx.lineTo(points[i].x, points[i].y);
  }
  sCtx.lineTo(points[points.length - 1].x, height);
  sCtx.closePath();
  
  const fillGrad = sCtx.createLinearGradient(0, 0, 0, height);
  fillGrad.addColorStop(0, 'rgba(244, 244, 246, 0.03)');
  fillGrad.addColorStop(1, 'rgba(244, 244, 246, 0.0)');
  sCtx.fillStyle = fillGrad;
  sCtx.fill();
}

function updateGauge(score) {
  const offset = GAUGE_CIRCUMFERENCE - (score / 100) * GAUGE_CIRCUMFERENCE;
  scoreGaugeFill.style.strokeDashoffset = offset;
  
  if (score >= 85) {
    scoreGaugeFill.style.stroke = 'var(--color-secondary)';
  } else if (score >= 50) {
    scoreGaugeFill.style.stroke = 'var(--color-warning)';
  } else {
    scoreGaugeFill.style.stroke = 'var(--color-danger)';
  }
}

// --- Canvas Skeletal Rendering ---
// --- Canvas Skeletal Rendering ---
function drawSkeleton(landmarks, analysisOrViolating, frameBase64 = null) {
  if (!isMonitoring) {
    clearCanvas();
    return;
  }

  let analysis = null;
  if (analysisOrViolating && typeof analysisOrViolating === 'object') {
    analysis = analysisOrViolating;
  }

  if (frameBase64) {
    const img = new Image();
    img.onload = () => {
      if (!isMonitoring) {
        clearCanvas();
        return;
      }
      // Dynamically adjust canvas resolution to match camera native feed
      if (canvas.width !== img.naturalWidth || canvas.height !== img.naturalHeight) {
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        canvas.parentNode.style.aspectRatio = `${img.naturalWidth} / ${img.naturalHeight}`;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      if (landmarks) {
        renderSkeletonOverlay(landmarks, analysis);
      }
    };
    img.src = 'data:image/jpeg;base64,' + frameBase64;
  } else {
    // Standalone / Simulation Mode fallback (draw deep obsidian background)
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (landmarks) {
      renderSkeletonOverlay(landmarks, analysis);
    }
  }
}

function renderSkeletonOverlay(landmarks, analysis) {
  const points = {};
  for (const [id, pt] of Object.entries(landmarks)) {
    // X coordinates are already mirrored in the Python backend frame flip
    points[id] = {
      x: pt.x * canvas.width,
      y: pt.y * canvas.height
    };
  }

  const hasPts = (...ids) => ids.every(id => points[id]);

  if (hasPts(7, 8, 0, 11, 12)) {
    const midEars = {
      x: (points[7].x + points[8].x) / 2,
      y: (points[7].y + points[8].y) / 2
    };
    const midShoulders = {
      x: (points[11].x + points[12].x) / 2,
      y: (points[11].y + points[12].y) / 2
    };

    const colors = {
      default: '#f4f4f6', // Solid off-white
      warning: '#fbbf24', // Amber
      danger: '#f87171'   // Crimson
    };

    const scoreVal = parseFloat(scoreNumber.textContent) || 100;
    const violationColor = scoreVal < 60 ? colors.danger : colors.warning;

    const isSlouch = !!(analysis && analysis.violations && analysis.violations.slouch);
    const isFhp = !!(analysis && analysis.violations && analysis.violations.forward_head);
    const isAsymmetric = !!(analysis && analysis.violations && analysis.violations.lateral_asymmetry);

    const neckColor = isSlouch ? violationColor : colors.default;
    const headColor = isFhp ? violationColor : colors.default;
    const shoulderColor = isAsymmetric ? violationColor : colors.default;
    const earsColor = colors.default;

    // Draw connection lines
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'transparent';

    // 1. Ear-to-Ear
    ctx.strokeStyle = earsColor;
    ctx.beginPath();
    ctx.moveTo(points[7].x, points[7].y);
    ctx.lineTo(points[8].x, points[8].y);
    ctx.stroke();

    // 2. Midpoint Ears to Nose (Head tilt / FHP)
    ctx.strokeStyle = headColor;
    ctx.beginPath();
    ctx.moveTo(midEars.x, midEars.y);
    ctx.lineTo(points[0].x, points[0].y);
    ctx.stroke();

    // 3. Neck line (Slouch)
    ctx.strokeStyle = neckColor;
    ctx.beginPath();
    ctx.moveTo(midEars.x, midEars.y);
    ctx.lineTo(midShoulders.x, midShoulders.y);
    ctx.stroke();

    // 4. Shoulder-to-Shoulder (Shoulder axis)
    ctx.strokeStyle = shoulderColor;
    ctx.beginPath();
    ctx.moveTo(points[11].x, points[11].y);
    ctx.lineTo(points[12].x, points[12].y);
    ctx.stroke();

    // Draw joints as white dots with outlines matching the state of the line segments they connect to
    const drawJoint = (p, borderColor) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, 2 * Math.PI);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = 2.5;
      ctx.stroke();
    };

    drawJoint(points[0], headColor);
    drawJoint(points[7], isFhp ? violationColor : colors.default);
    drawJoint(points[8], isFhp ? violationColor : colors.default);
    drawJoint(points[11], isAsymmetric ? violationColor : (isSlouch ? violationColor : colors.default));
    drawJoint(points[12], isAsymmetric ? violationColor : (isSlouch ? violationColor : colors.default));
  }
}

// --- Notifications ---
async function requestNotificationPermission() {
  // 1. Request Tauri Notification permission
  if (window.__TAURI__ && window.__TAURI__.notification) {
    try {
      await window.__TAURI__.notification.requestPermission();
    } catch (e) {
      console.error('Failed to request Tauri notification permission:', e);
    }
  }
  // 2. Request HTML5 Notification permission
  if ('Notification' in window) {
    try {
      await Notification.requestPermission();
    } catch (e) {
      console.error('Failed to request HTML5 notification permission:', e);
    }
  }
}

let lastNotificationTime = 0;

async function triggerPostureAlert(title, bodyText) {
  violationCount++;
  statViolations.textContent = violationCount;
  
  const now = Date.now();
  if (now - lastNotificationTime < 60000) {
    console.log(`Notification cooldown active. Skipping desktop alert: [${title}] ${bodyText}`);
    return;
  }
  
  let notificationSent = false;

  // 1. Try Tauri Plugin Notification
  if (window.__TAURI__ && window.__TAURI__.notification) {
    try {
      let permissionGranted = await window.__TAURI__.notification.isPermissionGranted();
      if (!permissionGranted) {
        const permission = await window.__TAURI__.notification.requestPermission();
        permissionGranted = permission === 'granted';
      }
      if (permissionGranted) {
        window.__TAURI__.notification.sendNotification({
          title: title,
          body: bodyText
        });
        notificationSent = true;
      }
    } catch (e) {
      console.error('Tauri notification error:', e);
    }
  }

  // 2. Try Standard HTML5 Web Notification as fallback
  if (!notificationSent && 'Notification' in window) {
    try {
      if (Notification.permission === 'granted') {
        new Notification(title, {
          body: bodyText,
          icon: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23ee4d5f"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>'
        });
        notificationSent = true;
      } else if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          new Notification(title, {
            body: bodyText,
            icon: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23ee4d5f"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>'
          });
          notificationSent = true;
        }
      }
    } catch (e) {
      console.error('HTML5 notification error:', e);
    }
  }

  if (notificationSent) {
    lastNotificationTime = now;
  } else {
    console.log(`System Notification Alert (Fallback): [${title}] ${bodyText}`);
  }
}

// --- Standalone Simulation Engine ---
function switchToSimulation() {
  handleStartMonitoring(true);
  simTime = 0;
  
  // Create simulated calibration initially
  simBaseline.slouchDelta = 0.25;
  simBaseline.fhpRatio = 0.33;
  simBaseline.shoulderWidth = 0.30;
  simBaseline.calibrated = true;
  
  ratingBadge.className = 'rating-badge excellent';
  ratingBadge.textContent = 'Calibrated (Demo)';
  ratingDesc.textContent = 'Running standalone demo mode. Click Calibrate to re-center.';

  simulationInterval = setInterval(runSimulationLoop, 200);
}

function startMockCalibration() {
  mockCalibrationActive = true;
  mockCalibrationCountdown = 6; // 3 seconds total (checked every 0.5s)
  calibrationOverlay.classList.remove('hidden');
}

function runSimulationLoop() {
  simTime += 0.2;
  
  if (mockCalibrationActive) {
    mockCalibrationCountdown -= 1;
    calibrationCounter.textContent = Math.ceil(mockCalibrationCountdown / 2);
    
    // In calibration, output absolute perfect upright posture
    const cleanLandmarks = generateMockLandmarks('perfect');
    drawSkeleton(cleanLandmarks, false);
    
    if (mockCalibrationCountdown <= 0) {
      mockCalibrationActive = false;
      calibrationOverlay.classList.add('hidden');
      
      // Compute and save mock baseline values
      const ears_y = (cleanLandmarks[7].y + cleanLandmarks[8].y) / 2.0;
      const shoulders_y = (cleanLandmarks[11].y + cleanLandmarks[12].y) / 2.0;
      simBaseline.slouchDelta = Math.max(0.01, shoulders_y - ears_y);
      
      const nose_to_mid_ears = distance(cleanLandmarks[0], midpoint(cleanLandmarks[7], cleanLandmarks[8]));
      simBaseline.shoulderWidth = distance(cleanLandmarks[11], cleanLandmarks[12]);
      simBaseline.fhpRatio = nose_to_mid_ears / simBaseline.shoulderWidth;
      simBaseline.calibrated = true;
      
      ratingBadge.className = 'rating-badge excellent';
      ratingBadge.textContent = 'Calibrated (Demo)';
      ratingDesc.textContent = 'Monitoring posture against your customized baseline.';
    }
    return;
  }
  
  // Cycle through posture states every 15 seconds:
  // 0s to 12s: Perfect
  // 12s to 24s: Slouching
  // 24s to 36s: Forward Head Protraction (FHP)
  // 36s to 48s: Lateral Asymmetry (shoulder lean)
  // 48s+: Loop resets
  const cycle = Math.floor(simTime) % 48;
  let state = 'perfect';
  
  if (cycle >= 12 && cycle < 24) {
    state = 'slouch';
  } else if (cycle >= 24 && cycle < 36) {
    state = 'fhp';
  } else if (cycle >= 36 && cycle < 48) {
    state = 'asymmetry';
  }
  
  const landmarks = generateMockLandmarks(state);
  
  const analysis = evaluateMockBiomechanics(landmarks);
  
  drawSkeleton(landmarks, analysis);
  updateUI(analysis);
}

function generateMockLandmarks(state) {
  // Base coordinates in perfect upright posture
  let nose = { x: 0.5, y: 0.28 };
  let earL = { x: 0.45, y: 0.23 };
  let earR = { x: 0.55, y: 0.23 };
  let shoulderL = { x: 0.35, y: 0.48 };
  let shoulderR = { x: 0.65, y: 0.48 };
  
  // Add subtle breathing sway
  const sway = Math.sin(simTime) * 0.005;
  nose.y += sway;
  earL.y += sway;
  earR.y += sway;
  
  if (state === 'slouch') {
    // Head collapses vertically down, shoulders stay constant
    const collapse = 0.08; 
    nose.y += collapse;
    earL.y += collapse;
    earR.y += collapse;
  } 
  
  else if (state === 'fhp') {
    // Head moves closer, eyes/ears expand, shoulder width constant
    earL.x -= 0.025;
    earR.x += 0.025;
    nose.y += 0.03; // head tilts down/forward slightly
  } 
  
  else if (state === 'asymmetry') {
    // Shoulder axis slopes, nose leans sideways
    shoulderL.y -= 0.05; // left shoulder up
    shoulderR.y += 0.05; // right shoulder down
    
    // Head shifts to the right (screen coordinates)
    nose.x += 0.03;
    earL.x += 0.03;
    earR.x += 0.03;
  }
  
  return {
    0: { ...nose, z: 0, visibility: 0.99 },
    7: { ...earL, z: 0, visibility: 0.99 },
    8: { ...earR, z: 0, visibility: 0.99 },
    11: { ...shoulderL, z: 0, visibility: 0.99 },
    12: { ...shoulderR, z: 0, visibility: 0.99 }
  };
}

function evaluateMockBiomechanics(landmarks) {
  if (!simBaseline.calibrated) {
    return { status: 'uncalibrated' };
  }
  
  const ears_y = (landmarks[7].y + landmarks[8].y) / 2.0;
  const shoulders_y = (landmarks[11].y + landmarks[12].y) / 2.0;
  const current_slouch_delta = shoulders_y - ears_y;
  
  const slouch_ratio = current_slouch_delta / simBaseline.slouchDelta;
  const is_slouching = slouch_ratio < 0.75; // 25% collapse
  
  const nose_to_mid_ears = distance(landmarks[0], midpoint(landmarks[7], landmarks[8]));
  const current_shoulder_width = distance(landmarks[11], landmarks[12]);
  
  const current_fhp_ratio = nose_to_mid_ears / Math.max(0.01, current_shoulder_width);
  const fhp_ratio_deviation = current_fhp_ratio / simBaseline.fhpRatio;
  const is_fhp = fhp_ratio_deviation > 1.25; // 25% scale increase
  
  const dy = landmarks[12].y - landmarks[11].y;
  const dx = landmarks[12].x - landmarks[11].x;
  const shoulder_slope = Math.abs(dx) > 0.001 ? dy / dx : 0.0;
  const is_asymmetric = Math.abs(shoulder_slope) > 0.15; // Slope limit
  
  let score = 100;
  if (is_slouching) score -= 40;
  if (is_fhp) score -= 30;
  if (is_asymmetric) score -= 30;
  score = Math.max(0, score);
  
  // Brightness cycles between 35 (too dark) and 95 (healthy) every 30s
  const brightnessCycle = Math.floor(simTime) % 60;
  const ambient_brightness = brightnessCycle < 20 ? 35 : 95;
  
  // Simulate screen distance (drops to 42-47 cm in fhp/slouch, else 60-65 cm)
  let screen_distance = 62;
  if (is_fhp || is_slouching) {
    screen_distance = 42 + (Math.floor(simTime) % 6);
  } else {
    screen_distance = 60 + (Math.floor(simTime) % 6);
  }
  
  // Compute simulated Concentration Index
  let lastConcentration = score;
  if (concentrationHistory.length > 0) {
    lastConcentration = concentrationHistory[concentrationHistory.length - 1];
  }
  const concentration_index = Math.round(score * 0.2 + lastConcentration * 0.8);

  return {
    status: 'calibrated',
    metrics: {
      slouch_ratio: slouch_ratio,
      fhp_deviation: fhp_ratio_deviation,
      shoulder_slope: shoulder_slope,
      score: score,
      ambient_brightness: ambient_brightness,
      concentration_index: concentration_index,
      screen_distance: screen_distance
    },
    violations: {
      slouch: is_slouching,
      forward_head: is_fhp,
      lateral_asymmetry: is_asymmetric
    }
  };
}

// Math helpers
function distance(p1, p2) {
  return Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2));
}

function midpoint(p1, p2) {
  return {
    x: (p1.x + p2.x) / 2,
    y: (p1.y + p2.y) / 2
  };
}

// --- Insights & SVG Drawing helper methods ---
function generateMockInsightsReport() {
  return {
    status: 'calibrated',
    recommendations: [
      "Your posture score drops by 35% after 3:00 PM. We recommend scheduling a standing break at 2:45 PM.",
      "Fatigue Trend: Your posture quality drops by 8.4 points per hour of sitting. Try taking shorter, more frequent focus intervals.",
      "Moderate slouching detected. Keep the live posture companion active to help reinforce upright habits."
    ],
    hourly_averages: [
      { hour: 9, label: "9:00 AM", score: 88.5 },
      { hour: 10, label: "10:00 AM", score: 92.0 },
      { hour: 11, label: "11:00 AM", score: 86.4 },
      { hour: 12, label: "12:00 PM", score: 82.1 },
      { hour: 13, label: "1:00 PM", score: 79.5 },
      { hour: 14, label: "2:00 PM", score: 81.0 },
      { hour: 15, label: "3:00 PM", score: 62.3 },
      { hour: 16, label: "4:00 PM", score: 68.0 },
      { hour: 17, label: "5:00 PM", score: 75.2 },
      { hour: 18, label: "6:00 PM", score: 80.1 }
    ],
    daily_scores: [
      { day: "Mon", score: 84.2 },
      { day: "Tue", score: 81.0 },
      { day: "Wed", score: 87.5 },
      { day: "Thu", score: 73.1 },
      { day: "Fri", score: 80.8 },
      { day: "Sat", score: 85.0 },
      { day: "Sun", score: 91.2 }
    ],
    focus_vs_healthy: {
      focus_mins: 285,
      healthy_mins: 198
    }
  };
}

function renderInsights(report) {
  if (!report || report.status === 'insufficient_data') {
    aiRecsContainer.innerHTML = `<p class="empty-state-text">Insufficient posture history logged yet. Keep monitoring to generate insights.</p>`;
    insightFocusTime.textContent = '0m';
    insightHealthyTime.textContent = '0m';
    hourlyChartContainer.innerHTML = `<p class="empty-state-text">Insufficient data to plot chart.</p>`;
    dailyChartContainer.innerHTML = `<p class="empty-state-text">Insufficient data to plot chart.</p>`;
    if (coachLogsVal) {
      coachLogsVal.textContent = '0 mins';
    }
    return;
  }

  const focusTime = report.focus_vs_healthy ? report.focus_vs_healthy.focus_mins : 0;
  const healthyTime = report.focus_vs_healthy ? report.focus_vs_healthy.healthy_mins : 0;
  insightFocusTime.textContent = `${focusTime}m`;
  insightHealthyTime.textContent = `${healthyTime}m`;
  
  if (coachLogsVal) {
    coachLogsVal.textContent = `${focusTime} mins`;
  }

  aiRecsContainer.innerHTML = '';
  if (report.recommendations && report.recommendations.length > 0) {
    report.recommendations.forEach(rec => {
      const card = document.createElement('div');
      let cardClass = 'recommendation-card';
      let iconSvg = '';
      
      if (rec.includes('drops by') || rec.includes('slump')) {
        cardClass += ' warning';
        iconSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
      } else if (rec.includes('Fatigue Trend') || rec.includes('strain') || rec.includes('strain detected')) {
        cardClass += ' danger';
        iconSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
      } else {
        cardClass += ' success';
        iconSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
      }
      
      card.className = cardClass;
      card.innerHTML = `
        <div class="recommendation-icon">${iconSvg}</div>
        <div class="recommendation-text">${rec}</div>
      `;
      aiRecsContainer.appendChild(card);
    });
  } else {
    aiRecsContainer.innerHTML = `<p class="empty-state-text">No custom suggestions generated yet. Keep tracking your workspace posture.</p>`;
  }

  if (report.hourly_averages && report.hourly_averages.length >= 2) {
    drawHourlyLineChart(report.hourly_averages);
  } else {
    hourlyChartContainer.innerHTML = `<p class="empty-state-text">Insufficient data logged today.</p>`;
  }

  if (report.daily_scores && report.daily_scores.length >= 2) {
    drawDailyBarChart(report.daily_scores);
  } else {
    dailyChartContainer.innerHTML = `<p class="empty-state-text">Insufficient data logged this week.</p>`;
  }
}

let chartTooltipEl = null;

function createChartTooltip() {
  if (document.getElementById('chart-tooltip')) {
    chartTooltipEl = document.getElementById('chart-tooltip');
    return;
  }
  chartTooltipEl = document.createElement('div');
  chartTooltipEl.id = 'chart-tooltip';
  chartTooltipEl.className = 'chart-tooltip';
  chartTooltipEl.style.position = 'absolute';
  chartTooltipEl.style.pointerEvents = 'none';
  chartTooltipEl.style.opacity = '0';
  chartTooltipEl.style.zIndex = '9999';
  document.body.appendChild(chartTooltipEl);
}

function showTooltip(e, label, score) {
  if (!chartTooltipEl) createChartTooltip();
  
  let scoreClass = 'excellent';
  if (score < 60) scoreClass = 'critical';
  else if (score < 85) scoreClass = 'warning';

  chartTooltipEl.innerHTML = `
    <span class="tooltip-label">${label}</span>
    <span class="tooltip-value ${scoreClass}">${score}%</span>
  `;
  
  chartTooltipEl.style.opacity = '1';
  chartTooltipEl.style.left = `${e.clientX + 15}px`;
  chartTooltipEl.style.top = `${e.clientY - 45}px`;
}

function hideTooltip() {
  if (chartTooltipEl) {
    chartTooltipEl.style.opacity = '0';
  }
}

function drawHourlyLineChart(data) {
  const width = 500;
  const height = 150;
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 15;
  const paddingBottom = 25;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const scores = data.map(d => d.score);
  const minScore = Math.min(...scores);
  const minY = Math.max(0, Math.min(60, Math.floor(minScore / 10) * 10 - 10));
  const maxY = 100;

  const yTicks = [minY, Math.round((minY + maxY) / 2), maxY];
  let gridLinesHtml = '';
  yTicks.forEach(tick => {
    const yVal = paddingTop + (1 - (tick - minY) / (maxY - minY)) * chartHeight;
    gridLinesHtml += `
      <line class="chart-grid-line" x1="${paddingLeft}" y1="${yVal}" x2="${width - paddingRight}" y2="${yVal}" />
      <text class="chart-text" x="${paddingLeft - 10}" y="${yVal + 3}" text-anchor="end">${tick}</text>
    `;
  });

  let points = [];
  data.forEach((d, idx) => {
    const x = paddingLeft + (idx / (data.length - 1)) * chartWidth;
    const y = paddingTop + (1 - (d.score - minY) / (maxY - minY)) * chartHeight;
    points.push({ x, y, label: d.label, score: d.score });
  });

  const pathD = points.map((p, idx) => (idx === 0 ? 'M' : 'L') + ` ${p.x} ${p.y}`).join(' ');
  const areaPathD = pathD + ` L ${points[points.length - 1].x} ${height - paddingBottom} L ${points[0].x} ${height - paddingBottom} Z`;

  let pointsHtml = '';
  let xLabelsHtml = '';
  const labelStep = Math.max(1, Math.ceil(data.length / 5));
  
  points.forEach((p, idx) => {
    pointsHtml += `
      <circle class="chart-point" cx="${p.x}" cy="${p.y}" r="4" />
    `;
    if (idx % labelStep === 0 || idx === data.length - 1) {
      xLabelsHtml += `
        <text class="chart-text" x="${p.x}" y="${height - 5}" text-anchor="middle">${p.label}</text>
      `;
    }
  });

  const svgContent = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="position: relative; overflow: visible;">
      <defs>
        <linearGradient id="chart-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--color-primary)" stop-opacity="0.25"/>
          <stop offset="100%" stop-color="var(--color-primary)" stop-opacity="0.00"/>
        </linearGradient>
      </defs>
      ${gridLinesHtml}
      <line class="chart-axis-line" x1="${paddingLeft}" y1="${height - paddingBottom}" x2="${width - paddingRight}" y2="${height - paddingBottom}" />
      <line class="chart-axis-line" x1="${paddingLeft}" y1="${paddingTop}" x2="${paddingLeft}" y2="${height - paddingBottom}" />
      <path class="chart-line-gradient-area" d="${areaPathD}" />
      <path class="chart-line" d="${pathD}" />
      ${pointsHtml}
      ${xLabelsHtml}
      <line id="hourly-guide-line" x1="0" y1="0" x2="0" y2="0" style="stroke: rgba(244, 244, 246, 0.3); stroke-width: 1.5; stroke-dasharray: 4 3; display: none;" />
      <circle id="hourly-active-point" cx="0" cy="0" r="6" style="fill: #ffffff; stroke: var(--color-primary); stroke-width: 3; display: none;" />
    </svg>
  `;
  hourlyChartContainer.innerHTML = svgContent;

  const svg = hourlyChartContainer.querySelector('.chart-svg');
  const guideLine = hourlyChartContainer.querySelector('#hourly-guide-line');
  const activePoint = hourlyChartContainer.querySelector('#hourly-active-point');
  
  if (svg) {
    svg.addEventListener('mousemove', (e) => {
      const rect = svg.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * width;
      
      let closestPt = null;
      let minDistance = Infinity;
      points.forEach(p => {
        const dist = Math.abs(p.x - mouseX);
        if (dist < minDistance) {
          minDistance = dist;
          closestPt = p;
        }
      });
      
      if (closestPt && minDistance < 40) {
        guideLine.setAttribute('x1', closestPt.x);
        guideLine.setAttribute('y1', paddingTop);
        guideLine.setAttribute('x2', closestPt.x);
        guideLine.setAttribute('y2', height - paddingBottom);
        guideLine.style.display = 'block';
        
        activePoint.setAttribute('cx', closestPt.x);
        activePoint.setAttribute('cy', closestPt.y);
        activePoint.style.display = 'block';
        
        showTooltip(e, closestPt.label, closestPt.score);
      } else {
        guideLine.style.display = 'none';
        activePoint.style.display = 'none';
        hideTooltip();
      }
    });
    
    svg.addEventListener('mouseleave', () => {
      guideLine.style.display = 'none';
      activePoint.style.display = 'none';
      hideTooltip();
    });
  }
}

function drawDailyBarChart(data) {
  const width = 500;
  const height = 150;
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 15;
  const paddingBottom = 25;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const yTicks = [0, 50, 100];
  let gridLinesHtml = '';
  yTicks.forEach(tick => {
    const yVal = paddingTop + (1 - tick / 100) * chartHeight;
    gridLinesHtml += `
      <line class="chart-grid-line" x1="${paddingLeft}" y1="${yVal}" x2="${width - paddingRight}" y2="${yVal}" />
      <text class="chart-text" x="${paddingLeft - 10}" y="${yVal + 3}" text-anchor="end">${tick}</text>
    `;
  });

  const barCount = data.length;
  const singleBarSpace = chartWidth / barCount;
  const barWidth = singleBarSpace * 0.5;

  let barsHtml = '';
  let xLabelsHtml = '';

  data.forEach((d, idx) => {
    const x = paddingLeft + idx * singleBarSpace + (singleBarSpace - barWidth) / 2;
    const hVal = (d.score / 100) * chartHeight;
    const y = height - paddingBottom - hVal;
    
    let barColor = 'var(--color-primary)';
    if (d.score >= 85) {
      barColor = 'var(--color-secondary)';
    } else if (d.score < 60 && d.score > 0) {
      barColor = 'var(--color-danger)';
    } else if (d.score > 0) {
      barColor = 'var(--color-warning)';
    } else {
      barColor = 'rgba(255, 255, 255, 0.05)';
    }

    if (d.score > 0) {
      barsHtml += `
        <rect class="chart-bar" x="${x}" y="${y}" width="${barWidth}" height="${hVal}" fill="${barColor}" style="transition: filter 0.15s ease, fill 0.15s ease; cursor: pointer;" />
      `;
    } else {
      barsHtml += `
        <rect class="chart-bar" x="${x}" y="${height - paddingBottom - 4}" width="${barWidth}" height="4" fill="rgba(255, 255, 255, 0.05)" />
      `;
    }

    xLabelsHtml += `
      <text class="chart-text" x="${x + barWidth / 2}" y="${height - 5}" text-anchor="middle">${d.day}</text>
    `;
  });

  const svgContent = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="position: relative; overflow: visible;">
      ${gridLinesHtml}
      <line class="chart-axis-line" x1="${paddingLeft}" y1="${height - paddingBottom}" x2="${width - paddingRight}" y2="${height - paddingBottom}" />
      <line class="chart-axis-line" x1="${paddingLeft}" y1="${paddingTop}" x2="${paddingLeft}" y2="${height - paddingBottom}" />
      ${barsHtml}
      ${xLabelsHtml}
    </svg>
  `;
  dailyChartContainer.innerHTML = svgContent;

  const svg = dailyChartContainer.querySelector('.chart-svg');
  if (svg) {
    const bars = svg.querySelectorAll('.chart-bar');
    bars.forEach((bar, idx) => {
      const item = data[idx];
      if (item && item.score > 0) {
        bar.addEventListener('mouseenter', (e) => {
          bar.style.filter = 'brightness(1.25)';
          showTooltip(e, item.day, item.score);
        });
        bar.addEventListener('mousemove', (e) => {
          showTooltip(e, item.day, item.score);
        });
        bar.addEventListener('mouseleave', () => {
          bar.style.filter = 'none';
          hideTooltip();
        });
      }
    });
  }
}

// --- AI Coach Chat System Helpers ---
function handleSendChatMessage() {
  const query = chatInput.value.trim();
  if (!query) return;

  // Append user message bubble to viewport
  appendChatMessage('user', query);
  chatInput.value = '';

  // Show typing indicator
  showChatTypingIndicator();

  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      action: 'chat',
      message: query
    }));
  } else {
    // If socket is not open, simulate mock response after a brief delay
    setTimeout(() => {
      removeChatTypingIndicator();
      const mockReply = generateMockChatReply(query);
      appendChatMessage('assistant', mockReply);
    }, 1000);
  }
}

function appendChatMessage(sender, text) {
  const messageElement = document.createElement('div');
  messageElement.className = `chat-message ${sender}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  
  if (sender === 'assistant') {
    bubble.innerHTML = formatMarkdown(text);
  } else {
    const p = document.createElement('p');
    p.textContent = text;
    bubble.appendChild(p);
  }
  
  messageElement.appendChild(bubble);
  chatMessages.appendChild(messageElement);
  
  // Scroll to bottom of viewport
  const viewport = document.querySelector('.chat-viewport');
  if (viewport) {
    viewport.scrollTop = viewport.scrollHeight;
  }
}

function showChatTypingIndicator() {
  if (document.getElementById('chat-typing-indicator')) return;

  const indicator = document.createElement('div');
  indicator.className = 'chat-message assistant';
  indicator.id = 'chat-typing-indicator';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  
  bubble.innerHTML = `
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  
  indicator.appendChild(bubble);
  chatMessages.appendChild(indicator);

  const viewport = document.querySelector('.chat-viewport');
  if (viewport) {
    viewport.scrollTop = viewport.scrollHeight;
  }
}

function removeChatTypingIndicator() {
  const indicator = document.getElementById('chat-typing-indicator');
  if (indicator) {
    indicator.remove();
  }
}

function formatMarkdown(text) {
  let html = text;
  // Escape HTML tags to prevent XSS
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  
  // Headers (### Header)
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.*?)_/g, '<em>$1</em>');
  
  // Bullet lists
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
  
  // Replace newlines with <br>
  html = html.replace(/\n/g, '<br>');
  
  return html;
}

function generateMockChatReply(query) {
  const q = query.toLowerCase();
  
  if (q.includes('neck') || q.includes('pain') || q.includes('sore') || q.includes('back') || q.includes('shoulder')) {
    return `### 🧘 Posture & Neck Stretch (Simulation Mode)
I noticed you asked about neck or back discomfort. 

**Ergonomic Tips:**
- **Monitor Height:** Raise your monitor so the top third of the screen is at eye level.
- **Micro-Stretch:** Roll your shoulders backward 10 times, then gently drop your ear to your shoulder for 10 seconds on each side.
- **Seat Support:** Maintain a 90-100 degree angle at your hips with solid lumbar support.`;
  }
  
  if (q.includes('eye') || q.includes('strain') || q.includes('blink') || q.includes('fatigue') || q.includes('light') || q.includes('bright') || q.includes('screen')) {
    return `### 👁️ Eye Strain & Ciliary Fatigue (Simulation Mode)
To reduce dry eyes and focusing strain:

**Recommended Guidelines:**
- **The 20-20-20 Rule:** Every 20 minutes, look at an object 20 feet away for 20 seconds.
- **Distance:** Keep your screen at least **50 cm** away from your face.
- **Lighting:** Align your screen brightness with ambient lighting to minimize glare.`;
  }
  
  if (q.includes('break') || q.includes('stretch') || q.includes('timer') || q.includes('schedule') || q.includes('exercise')) {
    return `### ⏱️ Standing & Stretching Breaks (Simulation Mode)
Frequent movement is the best counter to static load!

**Quick Break Routine:**
1. **Chest Opener (15s):** Interlace fingers behind your back and push your chest forward.
2. **Hip Flexor Stretch (20s):** Stand up, step back with one leg, and tilt your pelvis forward.
3. **Hydration:** Take a 2-minute walk to grab a glass of water.`;
  }

  if (q.includes('score') || q.includes('stats') || q.includes('how') || q.includes('progress') || q.includes('report')) {
    return `### 📊 Simulated Performance Report
Here is your current session dashboard summary:
- **Average Posture Score:** 88%
- **Focus Time:** 32 minutes
- **Break Adherence:** Good

Try to maintain an upright chest alignment to keep your score in the green!`;
  }

  return `### 🤖 ErgoLearn AI Coach (Simulation Mode)
Hello! I am your AI Ergonomic Coach.

Since we are running in **Offline/Simulation Mode**, I can provide general guide advice.
Try asking me:
- *"Give me a neck stretch"*
- *"How do I reduce eye strain?"*
- *"Suggest a standing break exercise"*`;
}
