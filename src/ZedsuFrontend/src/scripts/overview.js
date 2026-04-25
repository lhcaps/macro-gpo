// overview.js — Overview / Home page (Phase 14.7)
// Key fixes vs old version:
// 1. Skeleton rendered ONCE on load, never recreated during poll
// 2. DOM refs cached after skeleton render
// 3. Poll event handler updates textContent only — NO innerHTML
// 4. Returns cleanup function that removes the event listener
// 5. YOLO path truncated to filename, full path in tooltip

import { registerPage, unregisterPage } from './ui/page-lifecycle.js';
import { updateText, updateClass } from './ui/dom.js';

let container = null;
let refs = null; // cached DOM refs set after skeleton render
let lastScrollTop = 0; // remember scroll position across poll updates
let currentPage = null;

/**
 * Render skeleton HTML once. This runs ONCE when the page loads.
 * After this, renderOverview() only updates textContent of existing elements.
 */
function renderSkeleton() {
  container.innerHTML = `
    <div class="overview-page">
      <div class="overview-hero">
        <div class="hero-status-strip">
          <div class="status-dot" id="ov-status-dot"></div>
          <span class="hero-status-text" id="ov-status-text">IDLE</span>
          <span class="hero-sep">&#xB7;</span>
          <span class="hero-backend" id="ov-backend">Backend OK</span>
          <span class="hero-sep">&#xB7;</span>
          <span class="hero-combat" id="ov-combat"></span>
          <span class="hero-sep" id="ov-combat-sep" style="display:none">&#xB7;</span>
          <span class="hero-kills" id="ov-kills"></span>
          <span class="hero-sep" id="ov-kills-sep" style="display:none">&#xB7;</span>
          <span class="hero-match" id="ov-match"></span>
        </div>
        <div class="hero-actions">
          <button class="btn btn-primary btn-sm" id="ov-btn-start">Start</button>
          <button class="btn btn-secondary btn-sm" id="ov-btn-stop" disabled>Stop</button>
          <button class="btn btn-danger btn-sm" id="ov-btn-estop">E-Stop</button>
        </div>
      </div>

      <div class="overview-alert-banner" id="ov-alert" style="display:none">
        <div class="alert-banner-content">
          <div class="alert-banner-dot"></div>
          <div>
            <strong id="ov-alert-title">Setup issues detected</strong>
            <p class="alert-banner-detail" id="ov-alert-detail"></p>
          </div>
        </div>
        <button class="btn btn-sm btn-secondary" id="ov-btn-fix">Fix Setup &#x2192;</button>
      </div>

      <div class="overview-grid">
        <div class="metric-card">
          <div class="metric-card-header">
            <div class="metric-card-icon-sm"></div>
            <h3 class="metric-card-title">System</h3>
          </div>
          <div class="metric-card-body" id="ov-system-body">
            <div class="metric-row"><span class="metric-label">Backend</span><span class="health-badge health-ok" id="ov-hb">OK</span></div>
            <div class="metric-row"><span class="metric-label">Uptime</span><span class="metric-value font-mono" id="ov-uptime">&#x2014;</span></div>
            <div class="metric-row"><span class="metric-label">Latency</span><span class="metric-value font-mono" id="ov-latency">&#x2014;</span></div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-card-header">
            <div class="metric-card-icon-sm"></div>
            <h3 class="metric-card-title">Combat</h3>
          </div>
          <div class="metric-card-body" id="ov-combat-body">
            <div class="metric-row"><span class="metric-label">Match</span><span class="metric-value font-mono" id="ov-match-card">&#x2014;</span></div>
            <div class="metric-row"><span class="metric-label">State</span><span class="metric-value" id="ov-combat-state">&#x2014;</span></div>
            <div class="metric-row"><span class="metric-label">Kills</span><span class="metric-value font-mono text-accent" id="ov-kills-card">0</span></div>
            <div class="metric-row"><span class="metric-label">Elapsed</span><span class="metric-value font-mono" id="ov-elapsed">00:00</span></div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-card-header">
            <div class="metric-card-icon-sm"></div>
            <h3 class="metric-card-title">Detection</h3>
          </div>
          <div class="metric-card-body" id="ov-detection-body">
            <div class="metric-row"><span class="metric-label">YOLO Model</span><span class="metric-value font-mono" id="ov-yolo-model" title="">&#x2014;</span></div>
            <div class="metric-row"><span class="metric-label">YOLO Status</span><span class="health-badge health-warning" id="ov-yolo-status">NOT LOADED</span></div>
            <div class="metric-row"><span class="metric-label">Quality</span><span class="metric-value font-mono" id="ov-yolo-quality">&#x2014;</span></div>
          </div>
          <div class="metric-card-footer">
            <button class="btn btn-xs btn-secondary" onclick="ShellApi.navigateTo('detection')">Configure &#x2192;</button>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-card-header">
            <div class="metric-card-icon-sm"></div>
            <h3 class="metric-card-title">Notifications</h3>
          </div>
          <div class="metric-card-body" id="ov-discord-body">
            <div class="metric-row"><span class="metric-label">Webhook</span><span class="health-badge health-warning" id="ov-webhook-status">NOT SET</span></div>
            <div class="metric-row"><span class="metric-label">Events</span><span class="metric-value font-mono" id="ov-webhook-events">0 active</span></div>
          </div>
          <div class="metric-card-footer">
            <button class="btn btn-xs btn-secondary" onclick="ShellApi.navigateTo('discord')">Configure &#x2192;</button>
          </div>
        </div>
      </div>

      <div class="overview-quick-links">
        <button class="btn btn-secondary btn-sm" onclick="ShellApi.navigateTo('detection')">Detection</button>
        <button class="btn btn-secondary btn-sm" onclick="ShellApi.navigateTo('positions')">Positions</button>
        <button class="btn btn-secondary btn-sm" onclick="ShellApi.navigateTo('discord')">Discord</button>
        <button class="btn btn-secondary btn-sm" onclick="ShellApi.navigateTo('logs')">Logs</button>
      </div>
    </div>
  `;

  // Cache all refs after skeleton is in the DOM
  refs = {
    statusDot: document.getElementById('ov-status-dot'),
    statusText: document.getElementById('ov-status-text'),
    backend: document.getElementById('ov-backend'),
    combat: document.getElementById('ov-combat'),
    combatSep: document.getElementById('ov-combat-sep'),
    kills: document.getElementById('ov-kills'),
    killsSep: document.getElementById('ov-kills-sep'),
    match: document.getElementById('ov-match'),
    btnStart: document.getElementById('ov-btn-start'),
    btnStop: document.getElementById('ov-btn-stop'),
    btnEStop: document.getElementById('ov-btn-estop'),
    btnFix: document.getElementById('ov-btn-fix'),
    alertBanner: document.getElementById('ov-alert'),
    alertTitle: document.getElementById('ov-alert-title'),
    alertDetail: document.getElementById('ov-alert-detail'),
    hb: document.getElementById('ov-hb'),
    uptime: document.getElementById('ov-uptime'),
    latency: document.getElementById('ov-latency'),
    matchCard: document.getElementById('ov-match-card'),
    combatState: document.getElementById('ov-combat-state'),
    killsCard: document.getElementById('ov-kills-card'),
    elapsed: document.getElementById('ov-elapsed'),
    yoloModel: document.getElementById('ov-yolo-model'),
    yoloStatus: document.getElementById('ov-yolo-status'),
    yoloQuality: document.getElementById('ov-yolo-quality'),
    webhookStatus: document.getElementById('ov-webhook-status'),
    webhookEvents: document.getElementById('ov-webhook-events'),
  };

  // Wire hero action buttons
  refs.btnStart?.addEventListener('click', () => ShellApi.sendCommand('start'));
  refs.btnStop?.addEventListener('click', () => ShellApi.sendCommand('stop'));
  refs.btnEStop?.addEventListener('click', () => {
    if (confirm('Emergency stop?')) ShellApi.sendCommand('emergency_stop');
  });
  refs.btnFix?.addEventListener('click', () => ShellApi.navigateTo('detection'));

  // Remember scroll position
  container.addEventListener('scroll', () => {
    lastScrollTop = container.scrollTop;
  }, { passive: true });
}

/**
 * Update DOM from normalized state. This is called on EVERY poll event.
 * It only updates textContent / className — NO innerHTML, NO scroll reset.
 */
function renderOverview(state = {}) {
  if (!container || !refs) return;

  // Restore scroll position
  container.scrollTop = lastScrollTop;

  // Hero status strip
  const status = state.bot_status || 'idle';
  updateClass(refs.statusDot, `status-dot status-${status}`);
  updateText(refs.statusText, status.toUpperCase());

  if (refs.backend) {
    refs.backend.textContent = state.backend_health === 'ok' ? 'Backend OK' : 'Backend OFFLINE';
  }

  const combat = state.combat_state;
  if (combat) {
    updateText(refs.combat, combat);
    refs.combat.style.display = '';
    refs.combatSep.style.display = '';
  } else {
    updateText(refs.combat, '');
    refs.combat.style.display = 'none';
    refs.combatSep.style.display = 'none';
  }

  const kills = state.kills;
  if (kills > 0) {
    updateText(refs.kills, `${kills} kill${kills !== 1 ? 's' : ''}`);
    refs.kills.style.display = '';
    refs.killsSep.style.display = '';
  } else {
    updateText(refs.kills, '');
    refs.kills.style.display = 'none';
    refs.killsSep.style.display = 'none';
  }

  const matchNum = state.match_num;
  if (matchNum) {
    updateText(refs.match, `Match #${matchNum}`);
    refs.match.style.display = '';
  } else {
    updateText(refs.match, '');
    refs.match.style.display = 'none';
  }

  // Hero buttons
  const isRunning = status === 'running';
  if (refs.btnStart) refs.btnStart.disabled = isRunning;
  if (refs.btnStop) refs.btnStop.disabled = !isRunning;

  // Setup alert
  const issues = state.setup_issues || [];
  if (issues.length > 0) {
    refs.alertBanner.style.display = '';
    updateText(refs.alertTitle, `${issues.length} setup issue${issues.length > 1 ? 's' : ''} detected`);
    updateText(refs.alertDetail, issues.join(' \u00b7 '));
  } else {
    refs.alertBanner.style.display = 'none';
  }

  // System card
  if (refs.hb) {
    refs.hb.textContent = state.backend_health === 'ok' ? 'OK' : 'OFFLINE';
    refs.hb.className = `health-badge health-${state.backend_health === 'ok' ? 'ok' : 'error'}`;
  }
  updateText(refs.uptime, formatUptime(state.uptime));

  const lat = state.latency || 0;
  updateText(refs.latency, `${lat}ms`);
  if (refs.latency) {
    refs.latency.className = `metric-value font-mono ${lat > 200 ? 'text-error' : lat > 100 ? 'text-warning' : 'text-accent'}`;
  }

  // Combat card
  updateText(refs.matchCard, matchNum ? `#${matchNum}` : '\u2014');
  updateText(refs.combatState, combat ? combat.toUpperCase() : '\u2014');
  updateText(refs.killsCard, String(kills || 0));
  updateText(refs.elapsed, formatElapsed(state.elapsed));

  // Detection card
  const yoloPath = state.yolo_model;
  if (yoloPath) {
    const filename = yoloPath.split(/[/\\]/).pop();
    updateText(refs.yoloModel, filename);
    if (refs.yoloModel) refs.yoloModel.title = yoloPath; // full path in tooltip
  } else {
    updateText(refs.yoloModel, '\u2014');
    if (refs.yoloModel) refs.yoloModel.title = '';
  }

  if (refs.yoloStatus) {
    const yoloAvail = state.yolo_available;
    refs.yoloStatus.textContent = yoloAvail ? 'AVAILABLE' : 'NOT LOADED';
    refs.yoloStatus.className = `health-badge health-${yoloAvail ? 'ok' : 'warning'}`;
  }

  const quality = state.yolo_quality;
  updateText(refs.yoloQuality, quality ? quality.toFixed(1) : '\u2014');

  // Notifications card
  const hasWebhook = state.has_webhook;
  if (refs.webhookStatus) {
    refs.webhookStatus.textContent = hasWebhook ? 'CONFIGURED' : 'NOT SET';
    refs.webhookStatus.className = `health-badge health-${hasWebhook ? 'ok' : 'warning'}`;
  }

  const eventCount = (state.webhook_events || []).length;
  updateText(refs.webhookEvents, `${eventCount} active`);
}

function onStateUpdate(e) {
  renderOverview(e.detail);
}

function formatElapsed(seconds) {
  if (!seconds || seconds < 0) return '00:00';
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function formatUptime(seconds) {
  if (!seconds || seconds < 0) return '\u2014';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds/60)}m ${Math.floor(seconds%60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

// ============================================================
// Public API
// ============================================================

/**
 * Load the overview page into target container.
 * @param {Element} target
 * @returns {{cleanup: Function}}
 */
export function loadOverviewPage(target) {
  container = target;
  currentPage = 'overview';

  renderSkeleton();
  renderOverview(window.ShellApi?.getState() || {});

  // Register the global state-update listener
  window.addEventListener('zedsu:state-update', onStateUpdate);

  // Register with page lifecycle so shell.js can cleanup on navigate away
  registerPage('overview', container, cleanupOverviewPage);

  return { cleanup: cleanupOverviewPage };
}

/**
 * Cleanup function — MUST be called when leaving the page.
 * Removes event listener and clears refs.
 */
export function cleanupOverviewPage() {
  if (container) {
    container.removeEventListener('scroll', () => {
      lastScrollTop = container.scrollTop;
    });
  }
  window.removeEventListener('zedsu:state-update', onStateUpdate);
  unregisterPage('overview');
  container = null;
  refs = null;
  lastScrollTop = 0;
}
