// hud.js — HUD v2: dual-mode overlay controller
// Polls backend state and renders the compact/expanded HUD overlay.

const HUD_CONFIG = {
  pollInterval: 500,
  expanded: false,
  corner: 'top-right', // top-right, top-left, bottom-right, bottom-left
  opacity: 1.0,
  margin: 16,
};

let pollTimer = null;
let state = {
  status: 'idle',
  combat_state: null,
  kills: 0,
  match_num: null,
  elapsed: 0,
  latency: 0,
  intent: null,
  crowd_risk: null,
  yolo_status: null,
};

const hudOverlay = document.getElementById('hud-overlay');
const hudStatusDot = document.getElementById('hud-status-dot');
const hudStatusText = document.getElementById('hud-status-text');
const hudCombat = document.getElementById('hud-combat');
const hudLatency = document.getElementById('hud-latency');
const hudMatch = document.getElementById('hud-match');
const hudKills = document.getElementById('hud-kills');
const hudTime = document.getElementById('hud-time');
const hudIntent = document.getElementById('hud-intent');
const hudCrowd = document.getElementById('hud-crowd');
const hudYolo = document.getElementById('hud-yolo');
const hudExpanded = document.getElementById('hud-expanded');

// ============================================================
// State Normalization
// ============================================================

function normalizeBackendState(backendState) {
  if (!backendState) return state;

  const hud = backendState.hud || {};
  const combat = backendState.combat || {};

  let status = 'idle';
  const botStatus = hud.status || backendState.bot_status || 'idle';
  if (botStatus === 'running') status = 'running';
  else if (botStatus === 'paused') status = 'paused';
  else if (botStatus === 'degraded') status = 'degraded';
  else if (botStatus === 'error' || botStatus === 'emergency_stop') status = 'error';

  return {
    status,
    combat_state: combat.state || combat.combat_state || null,
    kills: combat.kills || 0,
    match_num: combat.match_num || hud.match_num || null,
    elapsed: hud.elapsed || 0,
    latency: hud.latency || 0,
    intent: combat.intent || hud.intent || null,
    crowd_risk: combat.crowd_risk || null,
    yolo_status: hud.yolo_status || null,
  };
}

// ============================================================
// HUD DOM Updates
// ============================================================

function updateHudDisplay() {
  if (!hudOverlay) return;

  // Status dot
  hudStatusDot.className = `status-dot status-${state.status}`;

  // Status text
  hudStatusText.textContent = state.status.toUpperCase();

  // Combat state
  hudCombat.textContent = state.combat_state
    ? state.combat_state.toUpperCase()
    : '—';

  // Latency
  hudLatency.textContent = `${state.latency}ms`;
  hudLatency.className = 'font-mono text-sm ' + (
    state.latency > 200 ? 'text-error' :
    state.latency > 100 ? 'text-warning' : 'text-cyan'
  );

  // Match info
  hudMatch.textContent = state.match_num ? `Match #${state.match_num}` : '—';

  // Kills
  hudKills.textContent = `Kills ${state.kills}`;

  // Elapsed time
  hudTime.textContent = formatElapsed(state.elapsed);

  // Expanded fields
  if (state.intent) {
    hudIntent.textContent = state.intent;
  } else {
    hudIntent.textContent = '—';
  }

  if (state.crowd_risk !== null && state.crowd_risk !== undefined) {
    const crowdColor = state.crowd_risk > 0.7 ? 'text-error' :
                       state.crowd_risk > 0.4 ? 'text-warning' : 'text-cyan';
    hudCrowd.textContent = state.crowd_risk.toFixed(2);
    hudCrowd.className = `font-mono text-xs ${crowdColor}`;
  } else {
    hudCrowd.textContent = '—';
  }

  if (state.yolo_status) {
    hudYolo.textContent = state.yolo_status;
  } else {
    hudYolo.textContent = '—';
  }
}

function formatElapsed(seconds) {
  if (!seconds || seconds < 0) return '00:00';
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

// ============================================================
// Backend Polling
// ============================================================

async function pollBackend() {
  try {
    const resp = await fetch('http://localhost:9761/state');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    state = normalizeBackendState(data);
    updateHudDisplay();
  } catch (err) {
    // Backend offline — show error state
    state.status = 'error';
    if (hudStatusDot) hudStatusDot.className = 'status-dot status-error';
    if (hudStatusText) hudStatusText.textContent = 'OFFLINE';
    if (hudCombat) hudCombat.textContent = '—';
    if (hudLatency) hudLatency.textContent = '—';
  }
}

// ============================================================
// Compact / Expanded Mode
// ============================================================

function toggleExpanded() {
  HUD_CONFIG.expanded = !HUD_CONFIG.expanded;
  if (hudExpanded) {
    hudExpanded.style.display = HUD_CONFIG.expanded ? 'block' : 'none';
  }
  if (hudOverlay) {
    hudOverlay.classList.toggle('hud-expanded-mode', HUD_CONFIG.expanded);
  }
}

// ============================================================
// Dynamic Corner Placement
// ============================================================

function applyCornerPlacement() {
  if (!hudOverlay) return;

  // Persist settings whenever placement changes
  try {
    localStorage.setItem('zedsu-hud-settings', JSON.stringify({
      corner: HUD_CONFIG.corner,
      opacity: HUD_CONFIG.opacity,
      expanded: HUD_CONFIG.expanded,
    }));
  } catch (e) {}

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const margin = HUD_CONFIG.margin;

  hudOverlay.style.top = 'auto';
  hudOverlay.style.bottom = 'auto';
  hudOverlay.style.left = 'auto';
  hudOverlay.style.right = 'auto';

  switch (HUD_CONFIG.corner) {
    case 'top-right':
      hudOverlay.style.top = `${margin}px`;
      hudOverlay.style.right = `${margin}px`;
      break;
    case 'top-left':
      hudOverlay.style.top = `${margin}px`;
      hudOverlay.style.left = `${margin}px`;
      break;
    case 'bottom-right':
      hudOverlay.style.bottom = `${margin}px`;
      hudOverlay.style.right = `${margin}px`;
      break;
    case 'bottom-left':
      hudOverlay.style.bottom = `${margin}px`;
      hudOverlay.style.left = `${margin}px`;
      break;
  }

  // Apply opacity
  hudOverlay.style.opacity = HUD_CONFIG.opacity;
}

// ============================================================
// HUD Actions
// ============================================================

document.getElementById('hud-cycle-corner')?.addEventListener('click', function() {
  var corners = ['top-right', 'top-left', 'bottom-right', 'bottom-left'];
  var idx = corners.indexOf(HUD_CONFIG.corner);
  HUD_CONFIG.corner = corners[(idx + 1) % corners.length];
  applyCornerPlacement();
});

document.getElementById('hud-toggle-expand')?.addEventListener('click', function() {
  toggleExpanded();
  // Persist after toggle
  try {
    localStorage.setItem('zedsu-hud-settings', JSON.stringify({
      corner: HUD_CONFIG.corner,
      opacity: HUD_CONFIG.opacity,
      expanded: HUD_CONFIG.expanded,
    }));
  } catch (e) {}
});
document.getElementById('hud-toggle-pin')?.addEventListener('click', () => {
  hudOverlay?.classList.toggle('hud-pinned');
});

// ============================================================
// HUD Visibility API (called from Rust via Tauri invoke or window)
// ============================================================

window.HudApi = {
  show() { if (hudOverlay) { hudOverlay.style.display = 'block'; applyCornerPlacement(); } },
  hide() { if (hudOverlay) hudOverlay.style.display = 'none'; },
  toggle() {
    if (hudOverlay) {
      if (hudOverlay.style.display !== 'none') this.hide();
      else this.show();
    }
  },
  setCorner(corner) { HUD_CONFIG.corner = corner; applyCornerPlacement(); },
  setOpacity(opacity) { HUD_CONFIG.opacity = Math.max(0.7, Math.min(1.0, opacity)); applyCornerPlacement(); },
  setExpanded(expanded) {
    HUD_CONFIG.expanded = expanded;
    if (hudExpanded) hudExpanded.style.display = expanded ? 'block' : 'none';
  },
  pollBackend,
  updateState(newState) { state = { ...state, ...newState }; updateHudDisplay(); },
  getState() { return state; },
};

// ============================================================
// Initialization
// ============================================================

export function initHud() {
  if (!hudOverlay) return;

  // Load persisted settings from localStorage
  try {
    var saved = JSON.parse(localStorage.getItem('zedsu-hud-settings') || '{}');
    if (saved.corner) HUD_CONFIG.corner = saved.corner;
    if (saved.opacity !== undefined) HUD_CONFIG.opacity = saved.opacity;
    if (saved.expanded !== undefined) HUD_CONFIG.expanded = saved.expanded;
  } catch (e) {}

  // Restore expanded state
  if (HUD_CONFIG.expanded && hudExpanded) {
    hudExpanded.style.display = 'block';
  }

  // Clear any existing timer to prevent memory leaks on re-init
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }

  applyCornerPlacement();
  pollBackend();
  pollTimer = setInterval(pollBackend, HUD_CONFIG.pollInterval);

  window.addEventListener('resize', applyCornerPlacement);
}
