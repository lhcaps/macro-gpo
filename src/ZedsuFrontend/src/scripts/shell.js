// shell.js — Full Operator Shell implementation
// Includes: TopCommandBar, SidebarNav, command proxy, page routing, Toast, state normalization

const API_BASE = 'http://localhost:9761';

// Dynamic import for overview page
async function loadOverview() {
  const m = await import('./overview.js');
  m.loadOverviewPage(shellMain);
}

// ============================================================
// DOM References
// ============================================================
const topbarStatus = document.getElementById('topbar-status');
const topbarBackend = document.getElementById('topbar-backend');
const topbarMatch = document.getElementById('topbar-match');
const topbarCombat = document.getElementById('topbar-combat');
const topbarKills = document.getElementById('topbar-kills');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnEStop = document.getElementById('btn-estop');
const btnHud = document.getElementById('btn-hud');
const btnLogs = document.getElementById('btn-logs');
const btnRestart = document.getElementById('btn-restart');
const navItems = document.querySelectorAll('.nav-item');
const shellMain = document.getElementById('shell-main');

let currentPage = 'overview';
let pollTimer = null;
let cachedState = null;

// ============================================================
// Toast Notifications
// ============================================================
const Toast = {
  container: null,

  init() {
    if (!this.container) {
      this.container = document.getElementById('toast-container');
    }
  },

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  show(message, type = 'info', duration = 3000) {
    this.init();
    if (!this.container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-message">${this._escapeHtml(message)}</span>`;
    toast.style.animation = 'toast-enter 200ms ease-out forwards';
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = 'toast-exit 200ms ease-in forwards';
      setTimeout(() => toast.remove(), 200);
    }, duration);
  },

  success(msg) { this.show(msg, 'success'); },
  error(msg) { this.show(msg, 'error', 5000); },
  info(msg) { this.show(msg, 'info'); },
  warning(msg) { this.show(msg, 'warning', 4000); },
};

// Expose Toast globally
window.ShellApi = window.ShellApi || {};
window.ShellApi.Toast = Toast;

// ============================================================
// Command Proxy — { action, payload } contract
// ============================================================
async function sendCommand(action, payload = null) {
  try {
    const body = payload !== null
      ? { action, payload }
      : { action };
    const resp = await fetch(`${API_BASE}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || data.status === 'error') {
      Toast.error(data.message || data.error || `Command '${action}' failed`);
      return { success: false, error: data.message || data.error };
    }
    Toast.success(`${action} executed`);
    return data;
  } catch (err) {
    Toast.error(`Cannot reach backend: ${err.message}`);
    return { success: false, error: err.message };
  }
}

// ============================================================
// State Normalization — /state → UI contract
// ============================================================
function normalizeBackendState(data) {
  if (!data) return null;

  const hud = data.hud || {};
  const combat = data.combat || {};
  const discord = data.discord_events || {};
  const yolo = data.yolo_model || {};
  const setup = data.setup_issues || {};

  return {
    bot_status: hud.status || data.bot_status || 'idle',
    backend_health: data.backend_health || 'unknown',
    combat_state: combat.state || combat.combat_state || null,
    kills: combat.kills || 0,
    match_num: combat.match_num || hud.match_num || null,
    elapsed: hud.elapsed || 0,
    last_event: combat.last_event || null,
    intent: combat.intent || null,
    crowd_risk: combat.crowd_risk ?? null,
    death_reason: combat.death_reason || null,
    target_visible: combat.target_visible ?? null,
    latency: hud.latency || 0,
    has_webhook: discord.has_webhook || false,
    webhook_events: discord.events || [],
    yolo_available: yolo.available || false,
    yolo_model: yolo.model_name || yolo.active_model || null,
    yolo_quality: yolo.quality_score ?? null,
    setup_issues: setup.issues || [],
    uptime: data.uptime || 0,
    _raw: data,
  };
}

// ============================================================
// TopCommandBar Updates
// ============================================================
function updateTopbar(state) {
  if (!state) return;

  // Status pill
  if (topbarStatus) {
    topbarStatus.textContent = state.bot_status.toUpperCase();
    topbarStatus.className = `status-pill status-${state.bot_status}`;
  }

  // Backend health
  if (topbarBackend) {
    if (state.backend_health === 'ok') {
      topbarBackend.textContent = 'Backend OK';
      topbarBackend.className = 'backend-indicator backend-ok';
    } else if (state.backend_health === 'starting') {
      topbarBackend.textContent = 'Backend Starting';
      topbarBackend.className = 'backend-indicator backend-starting';
    } else {
      topbarBackend.textContent = 'Backend OFFLINE';
      topbarBackend.className = 'backend-indicator backend-offline';
    }
  }

  // Match info
  if (topbarMatch) {
    if (state.match_num) {
      topbarMatch.textContent = `Match #${state.match_num}`;
      topbarMatch.style.display = '';
    } else {
      topbarMatch.textContent = '';
      topbarMatch.style.display = 'none';
    }
  }

  // Combat state
  if (topbarCombat) {
    if (state.combat_state) {
      topbarCombat.textContent = state.combat_state;
      topbarCombat.style.display = '';
    } else {
      topbarCombat.textContent = '';
      topbarCombat.style.display = 'none';
    }
  }

  // Kills
  if (topbarKills) {
    if (state.kills > 0) {
      topbarKills.textContent = `${state.kills} kills`;
      topbarKills.style.display = '';
    } else {
      topbarKills.textContent = '';
      topbarKills.style.display = 'none';
    }
  }

  // Button states
  const isRunning = state.bot_status === 'running';
  if (btnStart) btnStart.disabled = isRunning;
  if (btnStop) btnStop.disabled = !isRunning;
}

// ============================================================
// Backend Polling
// ============================================================
async function pollBackend() {
  try {
    const resp = await fetch(`${API_BASE}/state`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    cachedState = normalizeBackendState(data);
    updateTopbar(cachedState);

    // Dispatch event for active page to update
    window.dispatchEvent(new CustomEvent('zedsu:state-update', { detail: cachedState }));
  } catch (_) {
    if (topbarBackend) {
      topbarBackend.textContent = 'Backend OFFLINE';
      topbarBackend.className = 'backend-indicator backend-offline';
    }
  }
}

// ============================================================
// Page Routing
// ============================================================
const pageModules = {
  overview: loadOverview,
  'combat-ai': () => import('./pages/combat-ai.js').then(m => m.load(shellMain)).catch(() => showPagePlaceholder(shellMain, 'Combat AI', '13-04')),
  detection: () => import('./pages/detection.js').then(m => m.load(shellMain)).catch(() => showPagePlaceholder(shellMain, 'Detection', '13-04')),
  positions: () => import('./pages/positions.js').then(m => m.load(shellMain)).catch(() => showPagePlaceholder(shellMain, 'Positions', '13-05')),
  discord: () => import('./pages/discord.js').then(m => m.load(shellMain)).catch(() => showPagePlaceholder(shellMain, 'Discord', '13-04')),
  yolo: () => import('./pages/yolo.js').then(m => m.load(shellMain)).catch(() => showPagePlaceholder(shellMain, 'YOLO', '13-04')),
  logs: () => import('./pages/logs.js').then(m => m.load(shellMain)).catch(() => showPagePlaceholder(shellMain, 'Logs', '13-04')),
  settings: () => import('./pages/settings.js').then(m => m.load(shellMain)).catch(() => showPagePlaceholder(shellMain, 'Settings', '13-04')),
};

function showPagePlaceholder(container, title, planRef) {
  if (!container) return;
  container.innerHTML = `
    <div class="page-placeholder">
      <div class="page-placeholder-icon">&#x25C8;</div>
      <h2>${title}</h2>
      <p>Full ${title} page is being built in plan ${planRef}.</p>
    </div>
  `;
}

async function navigateTo(page) {
  if (currentPage === page) return;
  currentPage = page;

  navItems.forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-page') === page);
  });

  if (!shellMain) return;
  shellMain.innerHTML = '<div class="page-loading"><div class="loading-spinner"></div></div>';

  try {
    const loader = pageModules[page];
    if (loader) {
      await loader();
    } else {
      showPagePlaceholder(shellMain, page, '13-04');
    }
  } catch (err) {
    console.error(`[Shell] Failed to load page '${page}':`, err);
    showPagePlaceholder(shellMain, page, '13-04');
  }
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
// Initialization
// ============================================================
export function initShell() {
  // Wire buttons
  btnStart?.addEventListener('click', () => sendCommand('start'));
  btnStop?.addEventListener('click', () => sendCommand('stop'));
  btnEStop?.addEventListener('click', () => {
    showConfirm('Emergency Stop', 'This will halt all bot actions immediately. Continue?', () => {
      Toast.warning('Emergency stop triggered');
      sendCommand('emergency_stop');
    });
  });
  btnHud?.addEventListener('click', () => window.HudApi?.toggle());
  btnRestart?.addEventListener('click', async () => {
    Toast.info('Restarting backend...');
    await sendCommand('restart_backend');
  });

  // Nav sidebar
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const page = item.getAttribute('data-page');
      navigateTo(page);
    });
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'F1') {
      e.preventDefault();
      showConfirm('Emergency Stop', 'This will halt all bot actions immediately. Continue?', () => {
        Toast.warning('Emergency stop');
        sendCommand('emergency_stop');
      });
    }
    if (e.key === 'F2') {
      window.HudApi?.toggle();
    }
    if (e.key === 'F3') {
      e.preventDefault();
      const isRunning = topbarStatus?.textContent === 'RUNNING';
      sendCommand(isRunning ? 'stop' : 'start');
    }
  });

  // Start polling
  pollBackend();
  pollTimer = setInterval(pollBackend, 2000);

  // Load default page
  navigateTo('overview');
}

// Expose to window
window.ShellApi = window.ShellApi || {};
Object.assign(window.ShellApi, {
  sendCommand,
  getState: () => cachedState,
  navigateTo,
  Toast,
  showConfirm,
});
