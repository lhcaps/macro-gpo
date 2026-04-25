// overview.js — Overview dashboard page (cockpit-first landing page)

const API_BASE = 'http://localhost:9761';
let container = null;

export function loadOverviewPage(target) {
  container = target;
  renderOverview();
  window.addEventListener('zedsu:state-update', onStateUpdate);
  return () => window.removeEventListener('zedsu:state-update', onStateUpdate);
}

function onStateUpdate(e) {
  renderOverview(e.detail);
}

function renderOverview(state = {}) {
  if (!container) return;

  const issues = state.setup_issues || [];
  const hasIssues = issues.length > 0;

  container.innerHTML = `
    <div class="overview-page">

      ${hasIssues ? `
      <div class="overview-alert-banner">
        <div class="alert-banner-content">
          <span class="alert-banner-icon">&#x26A0;</span>
          <div>
            <strong>${issues.length} setup issue${issues.length > 1 ? 's' : ''} detected</strong>
            <p class="alert-banner-detail">${issues.join(' \u00b7 ')}</p>
          </div>
        </div>
        <button class="btn btn-sm btn-secondary" onclick="ShellApi.navigateTo('detection')">
          Fix Setup &#x2192;
        </button>
      </div>
      ` : ''}

      <div class="overview-grid">

        <!-- Runtime Card -->
        <div class="metric-card">
          <div class="metric-card-header">
            <span class="metric-card-icon">&#x25C8;</span>
            <h3 class="metric-card-title">Runtime</h3>
          </div>
          <div class="metric-card-body">
            <div class="metric-row">
              <span class="metric-label">Bot Status</span>
              <span class="status-pill status-${state.bot_status || 'idle'}">${(state.bot_status || 'idle').toUpperCase()}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Backend</span>
              <span class="health-badge health-${state.backend_health === 'ok' ? 'ok' : 'unknown'}">${state.backend_health === 'ok' ? 'OK' : state.backend_health || 'UNKNOWN'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Uptime</span>
              <span class="metric-value font-mono">${formatUptime(state.uptime)}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Detection Latency</span>
              <span class="metric-value font-mono ${state.latency > 100 ? 'text-warning' : 'text-cyan'}">${state.latency}ms</span>
            </div>
            ${issues.length > 0 ? `
            <div class="metric-row">
              <span class="metric-label">Setup Issues</span>
              <span class="metric-value text-error">${issues.length}</span>
            </div>
            ` : ''}
          </div>
        </div>

        <!-- Current Match Card -->
        <div class="metric-card">
          <div class="metric-card-header">
            <span class="metric-card-icon">&#x2694;</span>
            <h3 class="metric-card-title">Current Match</h3>
          </div>
          <div class="metric-card-body">
            <div class="metric-row">
              <span class="metric-label">Match #</span>
              <span class="metric-value font-mono">${state.match_num ? `#${state.match_num}` : '&#x2014;'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Combat State</span>
              <span class="metric-value">${state.combat_state ? state.combat_state.toUpperCase() : '&#x2014;'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Kills</span>
              <span class="metric-value font-mono text-cyan">${state.kills || 0}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Elapsed</span>
              <span class="metric-value font-mono">${formatElapsed(state.elapsed)}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Last Event</span>
              <span class="metric-value text-muted">${state.last_event || '&#x2014;'}</span>
            </div>
          </div>
        </div>

        <!-- Combat AI Card -->
        <div class="metric-card">
          <div class="metric-card-header">
            <span class="metric-card-icon">&#x25CE;</span>
            <h3 class="metric-card-title">Combat AI</h3>
          </div>
          <div class="metric-card-body">
            <div class="metric-row">
              <span class="metric-label">Intent</span>
              <span class="metric-value text-ai">${state.intent || '&#x2014;'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Crowd Risk</span>
              <span class="metric-value font-mono ${state.crowd_risk > 0.7 ? 'text-error' : state.crowd_risk > 0.4 ? 'text-warning' : 'text-cyan'}">${state.crowd_risk !== null && state.crowd_risk !== undefined ? state.crowd_risk.toFixed(2) : '&#x2014;'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Target Visible</span>
              <span class="metric-value">${state.target_visible === true ? 'YES' : state.target_visible === false ? 'NO' : '&#x2014;'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Death Reason</span>
              <span class="metric-value text-muted">${state.death_reason || '&#x2014;'}</span>
            </div>
          </div>
          <div class="metric-card-footer">
            <button class="btn btn-xs btn-secondary" onclick="ShellApi.navigateTo('combat-ai')">View AI Config &#x2192;</button>
          </div>
        </div>

        <!-- Detection Card -->
        <div class="metric-card">
          <div class="metric-card-header">
            <span class="metric-card-icon">&#x25C9;</span>
            <h3 class="metric-card-title">Detection</h3>
          </div>
          <div class="metric-card-body">
            <div class="metric-row">
              <span class="metric-label">YOLO Model</span>
              <span class="metric-value font-mono">${state.yolo_model || '&#x2014;'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">YOLO Status</span>
              <span class="health-badge health-${state.yolo_available ? 'ok' : 'error'}">${state.yolo_available ? 'AVAILABLE' : 'NOT LOADED'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Quality Score</span>
              <span class="metric-value font-mono">${state.yolo_quality ? state.yolo_quality.toFixed(1) : '&#x2014;'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Detection Latency</span>
              <span class="metric-value font-mono ${state.latency > 100 ? 'text-warning' : 'text-cyan'}">${state.latency}ms</span>
            </div>
          </div>
          <div class="metric-card-footer">
            <button class="btn btn-xs btn-secondary" onclick="ShellApi.navigateTo('detection')">Setup Detection &#x2192;</button>
          </div>
        </div>

        <!-- Discord Card -->
        <div class="metric-card">
          <div class="metric-card-header">
            <span class="metric-card-icon">&#x25CC;</span>
            <h3 class="metric-card-title">Discord</h3>
          </div>
          <div class="metric-card-body">
            <div class="metric-row">
              <span class="metric-label">Webhook</span>
              <span class="health-badge health-${state.has_webhook ? 'ok' : 'warning'}">${state.has_webhook ? 'CONFIGURED' : 'NOT SET'}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">Events</span>
              <span class="metric-value font-mono">${state.webhook_events ? state.webhook_events.length : 0} active</span>
            </div>
          </div>
          <div class="metric-card-footer">
            <button class="btn btn-xs btn-secondary" onclick="ShellApi.navigateTo('discord')">Configure &#x2192;</button>
          </div>
        </div>

        <!-- Quick Actions Card -->
        <div class="metric-card metric-card-quick-actions">
          <div class="metric-card-header">
            <span class="metric-card-icon">&#x25B6;</span>
            <h3 class="metric-card-title">Quick Actions</h3>
          </div>
          <div class="metric-card-body quick-actions-grid">
            <button class="btn btn-primary btn-sm" onclick="ShellApi.sendCommand('start')">Start</button>
            <button class="btn btn-secondary btn-sm" onclick="ShellApi.sendCommand('stop')">Stop</button>
            <button class="btn btn-danger btn-sm" onclick="ShellApi.sendCommand('emergency_stop')">E-Stop</button>
            <button class="btn btn-secondary btn-sm" onclick="ShellApi.navigateTo('positions')">Positions</button>
            <button class="btn btn-secondary btn-sm" onclick="ShellApi.navigateTo('yolo')">YOLO</button>
            <button class="btn btn-secondary btn-sm" onclick="ShellApi.navigateTo('logs')">Logs</button>
          </div>
        </div>

      </div>
    </div>
  `;
}

function formatElapsed(seconds) {
  if (!seconds || seconds < 0) return '00:00';
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function formatUptime(seconds) {
  if (!seconds || seconds < 0) return '&#x2014;';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds/60)}m ${Math.floor(seconds%60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}
