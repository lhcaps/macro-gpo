// diagnostics.js — Diagnostics & QoL page (Phase 13-06)

var API_BASE = 'http://localhost:9761';

export async function load(container) {
  container.innerHTML = '<div class="page-loading"><div class="loading-spinner"></div></div>';

  container.innerHTML = [
    '<div class="diagnostics-page">',
    '  <div class="diagnostics-grid">',

    // Setup Issues
    '    <div class="diag-card">',
    '      <div class="diag-card-header">',
    '        <span class="diag-card-icon">\u26A0</span>',
    '        <h3>Setup Issues</h3>',
    '      </div>',
    '      <div class="diag-card-body" id="setup-issues-body">',
    '        <div class="page-loading" style="height:80px;"><div class="loading-spinner"></div></div>',
    '      </div>',
    '    </div>',

    // Event Timeline
    '    <div class="diag-card">',
    '      <div class="diag-card-header">',
    '        <span class="diag-card-icon">\u23F1</span>',
    '        <h3>Event Timeline</h3>',
    '      </div>',
    '      <div class="diag-card-body">',
    '        <div class="event-timeline" id="event-timeline">',
    '          <p class="text-sm text-muted">No recent events.</p>',
    '        </div>',
    '      </div>',
    '    </div>',

    // Folder Shortcuts
    '    <div class="diag-card">',
    '      <div class="diag-card-header">',
    '        <span class="diag-card-icon">\uD83D\uDCC1</span>',
    '        <h3>Quick Access</h3>',
    '      </div>',
    '      <div class="diag-card-body">',
    '        <div class="folder-shortcuts">',
    '          <button class="folder-shortcut" data-folder="config">',
    '            <span class="folder-icon">\u2699</span>',
    '            <div><span class="folder-name">Config</span><span class="folder-path">./config/</span></div>',
    '          </button>',
    '          <button class="folder-shortcut" data-folder="logs">',
    '            <span class="folder-icon">\uD83D\uDCCB</span>',
    '            <div><span class="folder-name">Logs</span><span class="folder-path">./logs/</span></div>',
    '          </button>',
    '          <button class="folder-shortcut" data-folder="runs">',
    '            <span class="folder-icon">\uD83D\uDCCA</span>',
    '            <div><span class="folder-name">Combat Runs</span><span class="folder-path">./runs/</span></div>',
    '          </button>',
    '          <button class="folder-shortcut" data-folder="yolo">',
    '            <span class="folder-icon">\uD83E\uDDE0</span>',
    '            <div><span class="folder-name">YOLO Models</span><span class="folder-path">./yolo/</span></div>',
    '          </button>',
    '        </div>',
    '      </div>',
    '    </div>',

    // Diagnostics Bundle
    '    <div class="diag-card">',
    '      <div class="diag-card-header">',
    '        <span class="diag-card-icon">\uD83D\uDCE6</span>',
    '        <h3>Diagnostics Bundle</h3>',
    '      </div>',
    '      <div class="diag-card-body">',
    '        <p class="text-sm text-muted" style="margin-bottom:12px;">Copy a diagnostics bundle with config (sanitized), system info.</p>',
    '        <div class="diag-actions">',
    '          <button class="btn btn-sm" id="btn-copy-bundle">Copy Bundle</button>',
    '          <button class="btn btn-sm" id="btn-download-bundle">Download</button>',
    '        </div>',
    '      </div>',
    '    </div>',

    '  </div>',
    '</div>',
  ].join('');

  // Wire folder shortcuts
  var shortcuts = container.querySelectorAll('.folder-shortcut');
  for (var i = 0; i < shortcuts.length; i++) {
    shortcuts[i].addEventListener('click', (function(btn) {
      var folderType = btn.getAttribute('data-folder');
      openFolder(folderType);
    }).bind(null, shortcuts[i]));
  }

  // Wire bundle buttons
  document.getElementById('btn-copy-bundle').addEventListener('click', copyBundle);
  document.getElementById('btn-download-bundle').addEventListener('click', downloadBundle);

  // Load data
  loadSetupIssues();
  loadEventTimeline();
}

function openFolder(type) {
  var folders = {
    config: 'config/',
    logs: 'logs/',
    runs: 'runs/',
    yolo: 'yolo/',
  };
  var folder = folders[type] || type;
  try {
    if (window.__TAURI__) {
      window.__TAURI__.shell.open(folder).catch(function() {
        window.ToastApi && window.ToastApi.info('Open folder: ' + folder);
      });
    } else {
      window.ToastApi && window.ToastApi.info('Open folder: ' + folder);
    }
  } catch (e) {
    window.ToastApi && window.ToastApi.info('Open folder: ' + folder);
  }
}

async function loadSetupIssues() {
  var body = document.getElementById('setup-issues-body');
  if (!body) return;

  try {
    var state = window.ShellApi ? window.ShellApi.getState() : null;
    var raw = state && state._raw ? state._raw : {};
    var config = raw.config || {};
    var hud = raw.hud || {};
    var combat = raw.combat || {};
    var yolo = raw.yolo_model || {};

    var issues = [];

    // Check for missing regions
    var regions = raw.regions || [];
    var regionNames = ['enemy_hp_bar', 'damage_numbers', 'player_hp_bar', 'incombat_timer', 'kill_icon'];
    for (var i = 0; i < regionNames.length; i++) {
      var found = false;
      for (var j = 0; j < regions.length; j++) {
        if (regions[j].name === regionNames[i] && (regions[j].x !== undefined || regions[j].w !== undefined)) {
          found = true; break;
        }
      }
      if (!found) issues.push('Region "' + regionNames[i] + '" not configured');
    }

    // Check for missing positions
    var positions = raw.positions || [];
    if (positions.length === 0) issues.push('No combat positions configured');

    // Check YOLO model
    if (!yolo.available) issues.push('YOLO model not loaded');

    if (issues.length === 0) {
      body.innerHTML = [
        '<div class="diag-success">',
        '  <span>\u2713</span>',
        '  <span>No setup issues detected. All systems operational.</span>',
        '</div>',
      ].join('');
    } else {
      var html = '';
      for (var k = 0; k < issues.length; k++) {
        html += [
          '<div class="issue-item">',
          '  <span class="issue-icon">\u26A0</span>',
          '  <span class="issue-text">' + escapeHtml(issues[k]) + '</span>',
          '</div>',
        ].join('');
      }
      body.innerHTML = html;
    }
  } catch (err) {
    body.innerHTML = '<p class="text-error">Failed to load setup issues</p>';
  }
}

async function loadEventTimeline() {
  var timeline = document.getElementById('event-timeline');
  if (!timeline) return;

  try {
    var state = window.ShellApi ? window.ShellApi.getState() : null;
    var raw = state && state._raw ? state._raw : {};
    var combat = raw.combat || {};
    var hud = raw.hud || {};
    var logs = raw.logs || [];

    var allEvents = [];

    if (combat.last_event) {
      allEvents.push({
        type: 'combat',
        message: combat.last_event,
        timestamp: combat.last_event_time || null,
      });
    }

    if (combat.death_reason) {
      allEvents.push({
        type: 'death',
        message: 'Death: ' + combat.death_reason,
        timestamp: combat.death_time || null,
      });
    }

    if (combat.intent) {
      allEvents.push({
        type: 'info',
        message: 'Intent: ' + combat.intent,
        timestamp: null,
      });
    }

    // Merge logs as info events (last 10)
    for (var i = 0; i < logs.length && i < 10; i++) {
      allEvents.push({ type: 'info', message: logs[i], timestamp: null });
    }

    if (allEvents.length === 0) {
      timeline.innerHTML = '<p class="text-sm text-muted">No recent events.</p>';
      return;
    }

    var typeIcons = {
      combat: '\u2694',
      death: '\uD83D\uDC80',
      info: '\u24D8',
      warning: '\u26A0',
      error: '\u2717',
    };

    var html = '';
    for (var j = 0; j < allEvents.length && j < 20; j++) {
      var event = allEvents[j];
      html += [
        '<div class="event-item event-' + (event.type || 'info') + '">',
        '  <span class="event-icon">' + (typeIcons[event.type] || '\u24D8') + '</span>',
        '  <div class="event-content">',
        '    <span class="event-message">' + escapeHtml(String(event.message || JSON.stringify(event))) + '</span>',
        (event.timestamp ? '<span class="event-time">' + formatTime(event.timestamp) + '</span>' : ''),
        '  </div>',
        '</div>',
      ].join('');
    }
    timeline.innerHTML = html;
  } catch (err) {
    timeline.innerHTML = '<p class="text-sm text-muted">Failed to load events.</p>';
  }
}

async function copyBundle() {
  try {
    var bundle = await generateBundle();
    var text = JSON.stringify(bundle, null, 2);
    await navigator.clipboard.writeText(text);
    window.ToastApi && window.ToastApi.success('Diagnostics bundle copied');
  } catch (err) {
    window.ToastApi && window.ToastApi.error('Failed to copy bundle');
  }
}

async function downloadBundle() {
  try {
    var bundle = await generateBundle();
    var blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'zedsu-diagnostics-' + Date.now() + '.json';
    a.click();
    URL.revokeObjectURL(url);
    window.ToastApi && window.ToastApi.success('Diagnostics downloaded');
  } catch (err) {
    window.ToastApi && window.ToastApi.error('Failed to download bundle');
  }
}

async function generateBundle() {
  var state = window.ShellApi ? window.ShellApi.getState() : null;
  var raw = state && state._raw ? state._raw : {};
  var config = raw.config || {};
  var combat = raw.combat || {};
  var hud = raw.hud || {};
  var yolo = raw.yolo_model || {};

  return {
    generated_at: new Date().toISOString(),
    version: 'Zedsu Phase 13',
    system: {
      platform: navigator.platform,
      userAgent: navigator.userAgent,
    },
    bot_status: hud.status || 'unknown',
    combat_stats: {
      kills: combat.kills || 0,
      match_num: combat.match_count || null,
      elapsed: hud.elapsed_sec || 0,
      last_event: combat.last_event || null,
      intent: combat.intent || null,
      crowd_risk: combat.crowd_risk || null,
    },
    config_summary: {
      has_webhook: !!(config.discord_events && config.discord_events.has_webhook),
      regions_count: (raw.regions || []).length,
      positions_count: (raw.positions || []).length,
      smart_combat_enabled: !!(config.smart_combat_detection),
      combat_ai_enabled: !!(config.combat_ai && config.combat_ai.telemetry && config.combat_ai.telemetry.enabled),
    },
    yolo_status: {
      available: !!yolo.available,
      model_name: yolo.model_path || yolo.active_model || null,
      quality_score: yolo.quality_score || null,
    },
  };
}

function formatTime(ts) {
  if (!ts) return '';
  try {
    return new Date(ts * 1000).toLocaleTimeString();
  } catch (e) {
    return String(ts);
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  var div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}
