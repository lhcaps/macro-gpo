// settings.js — System/Settings page (Runtime settings)
// Uses simple string concatenation for HTML to avoid escaping issues.

import * as api from '../shared/config-api.js';

function e(s) {
  if (s === null || s === undefined) return '';
  var d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

function toggle(id, checked, onchange) {
  var c = checked ? 'checked ' : '';
  return '<label class="toggle"><input type="checkbox" id="' + id + '" ' + c + 'onchange="' + onchange + '" /><span class="toggle-track"></span></label>';
}

export async function load(c) {
  c.innerHTML = '<div class="page-loading"><div class="loading-spinner"></div></div>';
  try {
    var state = window.ShellApi ? window.ShellApi.getState() : null;
    var config = (state && state._raw && state._raw.config) ? state._raw.config : await api.getConfig();
    var runtime = config.runtime || {};
    var version = (state && state.version) ? state.version : '1.0.0';
    var winTitle = e(runtime.window_title || '');

    var html = '<div class="settings-page">';

    // Game Window
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Game Window</h2></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Window Title</span><p class="setting-desc">Name of the game window to target</p></div>';
    html += '<input type="text" class="input input-sm" id="window-title" style="width:200px" value="' + winTitle + '" placeholder="e.g., Apex Legends" onchange="if(window.__settingsPage)window.__settingsPage.save()" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Auto-Focus Game</span><p class="setting-desc">Automatically bring game window to foreground before actions</p></div>';
    html += toggle('auto-focus', runtime.auto_focus, 'if(window.__settingsPage)window.__settingsPage.save()') + '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Require Focus</span><p class="setting-desc">Only send inputs when game window is focused</p></div>';
    html += toggle('require-focus', runtime.require_focus, 'if(window.__settingsPage)window.__settingsPage.save()') + '</div>';
    html += '</div></div>';

    // Scan Settings
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Scan Settings</h2></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Scan Interval (ms)</span><p class="setting-desc">Time between screen scans</p></div>';
    html += '<input type="number" class="input input-sm" id="scan-interval" style="width:80px" value="' + (runtime.scan_interval || 200) + '" min="50" max="2000" step="10" onchange="if(window.__settingsPage)window.__settingsPage.save()" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Move Interval (ms)</span><p class="setting-desc">Time between movement actions</p></div>';
    html += '<input type="number" class="input input-sm" id="move-interval" style="width:80px" value="' + (runtime.move_interval || 100) + '" min="10" max="1000" step="5" onchange="if(window.__settingsPage)window.__settingsPage.save()" /></div>';
    html += '</div></div>';

    // Key Bindings
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Key Bindings</h2></div><div class="section-card">';
    html += '<div class="setting-row"><span class="setting-label">Emergency Stop</span><span class="key-badge">F1</span></div>';
    html += '<div class="setting-row"><span class="setting-label">Toggle HUD</span><span class="key-badge">F2</span></div>';
    html += '<div class="setting-row"><span class="setting-label">Toggle Start/Stop</span><span class="key-badge">F3</span></div>';
    html += '<div class="setting-row"><span class="setting-label">Open Shell</span><span class="key-badge">F4</span></div>';
    html += '<p class="text-xs text-muted" style="margin-top:var(--space-3)">Custom key bindings for game actions are configured in the bot core (not exposed via UI).</p>';
    html += '</div></div>';

    // About
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">About</h2></div><div class="section-card">';
    html += '<div class="metric-row"><span class="metric-label">Version</span><span class="metric-value font-mono">' + version + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Phase</span><span class="metric-value">Phase 13 \u2014 Operator Shell Redesign</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Backend</span><span class="metric-value font-mono">localhost:9761</span></div>';
    html += '</div></div>';

    html += '</div>';
    c.innerHTML = html;

    window.__settingsPage = {
      save: function() {
        var w = document.getElementById('window-title');
        var af = document.getElementById('auto-focus');
        var rf = document.getElementById('require-focus');
        var si = document.getElementById('scan-interval');
        var mi = document.getElementById('move-interval');
        api.updateConfig({
          runtime: {
            window_title: w ? w.value : '',
            auto_focus: af ? af.checked : false,
            require_focus: rf ? rf.checked : false,
            scan_interval: si ? (parseInt(si.value) || 200) : 200,
            move_interval: mi ? (parseInt(mi.value) || 100) : 100,
          }
        }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Settings saved');
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to save settings');
          }
        });
      }
    };
  } catch (err) {
    c.innerHTML = '<div class="page-error"><p>Failed to load Settings page: ' + e(err.message) + '</p></div>';
  }
}
