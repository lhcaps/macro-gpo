// shell.js — Full Operator Shell (Phase 14.7)
// Key fix: page lifecycle cleanup — navigateTo() calls cleanup before loading new page.
// Each page module returns a cleanup function. Shell owns the cleanup registry.

import Toast from './toast.js';
import { registerPage, unregisterPage, isPageActive } from './ui/page-lifecycle.js';

const API_BASE = 'http://localhost:9761';

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

let currentPage = null; // Start null — first navigate triggers normal load flow
let pollTimer = null;
let cachedState = null;

// ============================================================
// Command Proxy — { action, payload } contract
// ============================================================
async function sendCommand(action, payload = null) {
  try {
    const body = payload !== null ? { action, payload } : { action };
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
  const config = data.config || {};
  const discord = config.discord_events || {};
  const yolo = data.yolo_model || {};
  const logs = data.logs || [];
  const running = !!data.running;

  const statusText = String(data.status || (running ? 'running' : 'idle')).toLowerCase();

  return {
    bot_status: running ? 'running' : statusText,
    backend_health: 'ok',
    combat_state: hud.combat_state || combat.state || combat.combat_state || null,
    kills: hud.kills ?? combat.kills ?? 0,
    match_num: hud.match_count ?? combat.match_count ?? null,
    elapsed: hud.elapsed_sec ?? 0,
    latency: hud.detection_ms ?? 0,
    intent: combat.intent || null,
    crowd_risk: combat.crowd_risk ?? null,
    death_reason: combat.death_reason || null,
    target_visible: combat.target_visible ?? null,
    has_webhook: !!discord.has_webhook,
    webhook_events: discord.events || [],
    yolo_available: !!yolo.available,
    yolo_model: yolo.model_path || yolo.active_model || null,
    yolo_quality: yolo.quality_score ?? null,
    logs,
    uptime: data.uptime_sec || data.uptime || 0,
    _raw: data,
  };
}

// ============================================================
// TopCommandBar Updates
// ============================================================
function updateTopbar(state) {
  if (!state) return;

  if (topbarStatus) {
    topbarStatus.textContent = state.bot_status.toUpperCase();
    topbarStatus.className = `status-pill status-${state.bot_status}`;
  }

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

  if (topbarMatch) {
    if (state.match_num) {
      topbarMatch.textContent = `Match #${state.match_num}`;
      topbarMatch.style.display = '';
    } else {
      topbarMatch.textContent = '';
      topbarMatch.style.display = 'none';
    }
  }

  if (topbarCombat) {
    if (state.combat_state) {
      topbarCombat.textContent = state.combat_state;
      topbarCombat.style.display = '';
    } else {
      topbarCombat.textContent = '';
      topbarCombat.style.display = 'none';
    }
  }

  if (topbarKills) {
    if (state.kills > 0) {
      topbarKills.textContent = `${state.kills} kills`;
      topbarKills.style.display = '';
    } else {
      topbarKills.textContent = '';
      topbarKills.style.display = 'none';
    }
  }

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
    // Dispatch event for the active page to update its own DOM elements
    window.dispatchEvent(new CustomEvent('zedsu:state-update', { detail: cachedState }));
  } catch (_) {
    if (topbarBackend) {
      topbarBackend.textContent = 'Backend OFFLINE';
      topbarBackend.className = 'backend-indicator backend-offline';
    }
  }
}

// ============================================================
// Page Routing with Lifecycle Cleanup
// ============================================================

function showPagePlaceholder(container, title) {
  if (!container) return;
  container.innerHTML = `
    <div class="page-placeholder">
      <div class="page-placeholder-icon">&#x25C8;</div>
      <h2>${title}</h2>
      <p>Full ${title} page is being built.</p>
    </div>
  `;
}

async function navigateTo(page) {
  if (currentPage === page) return;

  // Cleanup the previous page BEFORE loading the new one
  if (currentPage !== null) {
    unregisterPage(currentPage);
  }

  navItems.forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-page') === page);
  });

  if (!shellMain) return;
  shellMain.innerHTML = '<div class="page-loading"><div class="loading-spinner"></div></div>';

  try {
    const loader = pageModules[page];
    if (loader) {
      const mod = await loader();
      // mod.load() may return a cleanup function; register it for this page
      if (mod && typeof mod === 'object') {
        registerPage(page, shellMain, mod.cleanup || null);
      } else {
        registerPage(page, shellMain, null);
      }
    } else {
      showPagePlaceholder(shellMain, page);
    }
  } catch (err) {
    console.error(`[Shell] Failed to load page '${page}':`, err);
    showPagePlaceholder(shellMain, page);
  }

  currentPage = page;
}

// Page module loaders return { load, cleanup } — load is the existing async load function,
// cleanup is called by navigateTo via unregisterPage when leaving the page.
const pageModules = {
  overview: async () => {
    const m = await import('./overview.js');
    return { load: () => m.loadOverviewPage(shellMain), cleanup: m.cleanupOverviewPage };
  },
  'combat-ai': async () => {
    const m = await import('./pages/combat-ai.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'Combat AI'); return {}; }
    return { load: () => m.load(shellMain) };
  },
  detection: async () => {
    const m = await import('./pages/detection.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'Detection'); return {}; }
    return { load: () => m.load(shellMain) };
  },
  positions: async () => {
    const m = await import('./pages/positions.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'Positions'); return {}; }
    return { load: () => m.load(shellMain) };
  },
  discord: async () => {
    const m = await import('./pages/discord.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'Discord'); return {}; }
    return { load: () => m.load(shellMain), cleanup: m.cleanupDiscordPage };
  },
  yolo: async () => {
    const m = await import('./pages/yolo.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'YOLO'); return {}; }
    return { load: () => m.load(shellMain) };
  },
  logs: async () => {
    const m = await import('./pages/logs.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'Logs'); return {}; }
    return { load: () => m.load(shellMain), cleanup: m.cleanupLogsPage };
  },
  diagnostics: async () => {
    const m = await import('./pages/diagnostics.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'Diagnostics'); return {}; }
    return { load: () => m.load(shellMain) };
  },
  settings: async () => {
    const m = await import('./pages/settings.js').catch(() => null);
    if (!m) { showPagePlaceholder(shellMain, 'Settings'); return {}; }
    return { load: () => m.load(shellMain) };
  },
};

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
  btnStart?.addEventListener('click', () => sendCommand('start'));
  btnStop?.addEventListener('click', () => sendCommand('stop'));
  btnEStop?.addEventListener('click', () => {
    showConfirm('Emergency Stop', 'Halt all bot actions immediately?', () => {
      Toast.warning('Emergency stop triggered');
      sendCommand('emergency_stop');
    });
  });
  btnHud?.addEventListener('click', () => window.HudApi?.toggle());
  btnRestart?.addEventListener('click', async () => {
    Toast.info('Restarting backend...');
    await sendCommand('restart_backend');
  });

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const page = item.getAttribute('data-page');
      navigateTo(page);
    });
  });

  // Keyboard shortcuts — NO animations, instant response
  document.addEventListener('keydown', (e) => {
    if (e.key === 'F1') {
      e.preventDefault();
      showConfirm('Emergency Stop', 'Halt all bot actions immediately?', () => {
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

  // Start polling — updates topbar + dispatches state events
  pollBackend();
  pollTimer = setInterval(pollBackend, 2000);

  // Load default page (Home)
  navigateTo('overview');
}

window.ShellApi = window.ShellApi || {};
Object.assign(window.ShellApi, {
  sendCommand,
  getState: () => cachedState,
  navigateTo,
  Toast,
  showConfirm,
});
