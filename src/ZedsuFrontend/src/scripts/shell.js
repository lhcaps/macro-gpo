// shell.js — Operator Shell initialization
// Minimal version for now — full shell built in plan 13-03/13-04.

const topbarStatus = document.getElementById('topbar-status');
const topbarBackend = document.getElementById('topbar-backend');
const topbarMatch = document.getElementById('topbar-match');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnEStop = document.getElementById('btn-estop');
const btnHud = document.getElementById('btn-hud');
const btnLogs = document.getElementById('btn-logs');
const btnRestart = document.getElementById('btn-restart');

let currentState = { status: 'idle' };

// ============================================================
// Backend Polling
// ============================================================

async function pollShellState() {
  try {
    const resp = await fetch('http://localhost:9761/state');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    updateShellState(data);
  } catch (err) {
    if (topbarBackend) {
      topbarBackend.textContent = 'Backend OFFLINE';
      topbarBackend.className = 'backend-indicator backend-offline';
    }
  }
}

function updateShellState(data) {
  const hud = data.hud || {};
  const combat = data.combat || {};
  const botStatus = hud.status || data.bot_status || 'idle';

  // Status pill
  if (topbarStatus) {
    topbarStatus.textContent = botStatus.toUpperCase();
    topbarStatus.className = `status-pill status-${botStatus}`;
  }

  // Backend health
  if (topbarBackend) {
    topbarBackend.textContent = 'Backend OK';
    topbarBackend.className = 'backend-indicator backend-ok';
  }

  // Match info
  const matchNum = combat.match_num || hud.match_num;
  if (topbarMatch && matchNum) {
    topbarMatch.textContent = `Match #${matchNum}`;
  }

  currentState = { ...currentState, ...data };
}

// ============================================================
// Command Proxy
// ============================================================

async function sendCommand(action, payload = null) {
  try {
    const resp = await fetch('http://localhost:9761/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, payload }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || data.status === 'error') {
      window.ToastApi?.error(data.message || data.error || `HTTP ${resp.status}`);
    } else {
      window.ToastApi?.success(`${action} executed`);
    }
    return data;
  } catch (err) {
    window.ToastApi?.error(`Failed to send command: ${err.message}`);
    return { status: 'error', message: err.message };
  }
}

// ============================================================
// Button Handlers
// ============================================================

btnStart?.addEventListener('click', () => sendCommand('start'));
btnStop?.addEventListener('click', () => sendCommand('stop'));
btnEStop?.addEventListener('click', () => {
  showConfirm('Emergency Stop', 'This will halt all bot actions immediately. Continue?', () => {
    sendCommand('emergency_stop');
  });
});
btnRestart?.addEventListener('click', () => {
  window.ToastApi?.info('Restarting backend...');
  sendCommand('restart_backend');
});
btnHud?.addEventListener('click', () => window.HudApi?.toggle());

// ============================================================
// Navigation
// ============================================================

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    const page = item.getAttribute('data-page');
    loadShellPage(page);
  });
});

// ============================================================
// Page Loader (placeholders — full implementation in 13-03/13-04)
// ============================================================

function loadShellPage(page) {
  const main = document.getElementById('shell-main');
  if (!main) return;

  const pageContent = {
    overview: `
      <div class="page">
        <h1 class="page-title">Overview</h1>
        <div class="cards-grid">
          <div class="card">
            <div class="card-title">Runtime</div>
            <div class="metric-inline" style="margin-bottom:var(--space-4)">
              <span id="overview-status-dot" class="status-dot status-idle"></span>
              <span class="metric-label" id="overview-status-label">IDLE</span>
            </div>
            <div style="color:var(--color-text-muted);font-size:12px">
              <div style="margin-bottom:4px"><span class="backend-indicator backend-ok" id="overview-backend">Backend OK</span></div>
              <div id="overview-uptime">Uptime: --</div>
            </div>
          </div>
          <div class="card">
            <div class="card-title">Current Match</div>
            <div class="metric-value" id="overview-match">—</div>
            <div class="metric-label">Match #</div>
            <div style="margin-top:var(--space-3);display:flex;gap:var(--space-4)">
              <div>
                <div class="metric-value" id="overview-kills">0</div>
                <div class="metric-label">Kills</div>
              </div>
              <div>
                <div class="metric-value" id="overview-state">—</div>
                <div class="metric-label">State</div>
              </div>
            </div>
          </div>
          <div class="card">
            <div class="card-title">Combat AI</div>
            <div style="color:var(--color-text-muted);font-size:12px;margin-bottom:var(--space-3)">
              Intent <span id="ai-intent" class="text-cyan" style="float:right">—</span>
            </div>
            <div style="color:var(--color-text-muted);font-size:12px;margin-bottom:var(--space-3)">
              Crowd Risk <span id="ai-crowd" style="float:right">—</span>
            </div>
            <div style="color:var(--color-text-muted);font-size:12px">
              Target <span id="ai-target" style="float:right">—</span>
            </div>
          </div>
        </div>
      </div>`,
    'combat-ai': `
      <div class="page">
        <h1 class="page-title">Combat AI</h1>
        <p class="text-secondary" style="margin-bottom:var(--space-6)">Full page coming in Phase 13-04.</p>
      </div>`,
    detection: `
      <div class="page">
        <h1 class="page-title">Detection</h1>
        <p class="text-secondary" style="margin-bottom:var(--space-6)">Full page coming in Phase 13-04.</p>
      </div>`,
    positions: `
      <div class="page">
        <h1 class="page-title">Positions</h1>
        <p class="text-secondary" style="margin-bottom:var(--space-6)">Full page coming in Phase 13-05.</p>
      </div>`,
    discord: `
      <div class="page">
        <h1 class="page-title">Discord</h1>
        <p class="text-secondary" style="margin-bottom:var(--space-6)">Full page coming in Phase 13-04.</p>
      </div>`,
    yolo: `
      <div class="page">
        <h1 class="page-title">YOLO</h1>
        <p class="text-secondary" style="margin-bottom:var(--space-6)">Full page coming in Phase 13-04.</p>
      </div>`,
    logs: `
      <div class="page">
        <h1 class="page-title">Logs</h1>
        <p class="text-secondary" style="margin-bottom:var(--space-6)">Full page coming in Phase 13-06.</p>
      </div>`,
    settings: `
      <div class="page">
        <h1 class="page-title">Settings</h1>
        <p class="text-secondary" style="margin-bottom:var(--space-6)">Full page coming in Phase 13-04.</p>
      </div>`,
  };

  main.innerHTML = pageContent[page] || pageContent.overview;
  updateOverviewState();
}

// Update overview cards from current state
function updateOverviewState() {
  const hud = currentState.hud || {};
  const combat = currentState.combat || {};

  const statusDot = document.getElementById('overview-status-dot');
  const statusLabel = document.getElementById('overview-status-label');
  const matchEl = document.getElementById('overview-match');
  const killsEl = document.getElementById('overview-kills');
  const stateEl = document.getElementById('overview-state');
  const intentEl = document.getElementById('ai-intent');
  const crowdEl = document.getElementById('ai-crowd');
  const targetEl = document.getElementById('ai-target');

  const botStatus = hud.status || currentState.bot_status || 'idle';
  const matchNum = combat.match_num || hud.match_num;

  if (statusDot) statusDot.className = `status-dot status-${botStatus}`;
  if (statusLabel) statusLabel.textContent = botStatus.toUpperCase();
  if (matchEl) matchEl.textContent = matchNum || '—';
  if (killsEl) killsEl.textContent = combat.kills || 0;
  if (stateEl) stateEl.textContent = combat.state || '—';
  if (intentEl) intentEl.textContent = combat.intent || '—';
  if (crowdEl) crowdEl.textContent = combat.crowd_risk !== null && combat.crowd_risk !== undefined ? combat.crowd_risk.toFixed(2) : '—';
  if (targetEl) targetEl.textContent = '—'; // Will wire in 13-05
}

// ============================================================
// Confirm Dialog
// ============================================================

function showConfirm(title, message, onConfirm) {
  const overlay = document.getElementById('confirm-overlay');
  const titleEl = document.getElementById('confirm-title');
  const messageEl = document.getElementById('confirm-message');
  const okBtn = document.getElementById('confirm-ok');
  const cancelBtn = document.getElementById('confirm-cancel');

  if (!overlay) return;

  if (titleEl) titleEl.textContent = title;
  if (messageEl) messageEl.textContent = message;
  overlay.style.display = 'flex';

  const cleanup = () => {
    overlay.style.display = 'none';
    okBtn?.removeEventListener('click', handleOk);
    cancelBtn?.removeEventListener('click', handleCancel);
  };

  const handleOk = () => { cleanup(); onConfirm?.(); };
  const handleCancel = () => cleanup();

  okBtn?.addEventListener('click', handleOk);
  cancelBtn?.addEventListener('click', handleCancel);
}

// ============================================================
// Toast API stub (full implementation in 13-06)
// ============================================================

window.ToastApi = window.ToastApi || {
  success: (msg) => console.log('[Toast OK]', msg),
  error: (msg) => console.error('[Toast Error]', msg),
  info: (msg) => console.info('[Toast]', msg),
};

// ============================================================
// Shell Initialization
// ============================================================

export function initShell() {
  loadShellPage('overview');
  setInterval(pollShellState, 2000);
}
