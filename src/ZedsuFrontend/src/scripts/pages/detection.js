// detection.js — Combat Detection settings page
// Uses simple string concatenation for HTML.

import * as api from '../shared/config-api.js';

var REGIONS = ['enemy_hp_bar', 'damage_numbers', 'player_hp_bar', 'incombat_timer', 'kill_icon'];

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
    var regions = (state && state._raw && state._raw.regions) ? state._raw.regions : await api.getRegions().catch(function() { return []; });

    var regionMap = {};
    for (var i = 0; i < regions.length; i++) {
      regionMap[regions[i].name] = regions[i];
    }

    var smartCombat = config.smart_combat_detection !== false;
    var detectionEnabled = config.combat_detection_enabled !== false;
    var minEnemyHp = config.min_enemy_hp_pixels || 10;
    var minDmgNum = config.min_damage_number || 1;
    var playerHpThreshold = config.player_hp_threshold || 100;
    var incombatTimeout = config.incombat_timeout_sec || 3;
    var confidenceFloor = config.detection_confidence_floor || 0.3;

    var cardsHtml = '';
    for (var j = 0; j < REGIONS.length; j++) {
      var name = REGIONS[j];
      var region = regionMap[name];
      var hasRegion = region && (region.x !== undefined || region.w !== undefined);
      var status = hasRegion ? 'CONFIGURED' : 'NOT SET';
      var statusCls = hasRegion ? 'ok' : 'error';
      var displayName = name.replace(/_/g, ' ');
      var coords = '';
      if (hasRegion && region.x !== undefined) {
        coords = 'x:' + Math.round(region.x) + ' y:' + Math.round(region.y) + ' w:' + Math.round(region.w || 0) + ' h:' + Math.round(region.h || 0);
      }

      cardsHtml += '<div class="region-card">';
      cardsHtml += '<div class="region-card-header">';
      cardsHtml += '<span class="region-name font-mono">' + displayName + '</span>';
      cardsHtml += '<span class="health-badge health-' + statusCls + '">' + status + '</span>';
      cardsHtml += '</div>';
      cardsHtml += '<div class="region-card-body">';
      if (hasRegion) {
        cardsHtml += '<div class="font-mono text-xs text-muted">' + e(coords) + '</div>';
      } else {
        cardsHtml += '<p class="text-xs text-muted">No region configured</p>';
      }
      cardsHtml += '</div>';
      cardsHtml += '<div class="region-card-actions">';
      cardsHtml += '<button class="btn btn-xs btn-primary" onclick="if(window.__detectionPage)window.__detectionPage.pickRegion(\'' + name + '\')">' + (hasRegion ? 'Repick' : 'Pick') + '</button>';
      cardsHtml += '<button class="btn btn-xs" onclick="if(window.__detectionPage)window.__detectionPage.testRegion(\'' + name + '\')" ' + (hasRegion ? '' : 'disabled ') + '>Test</button>';
      cardsHtml += '<button class="btn btn-xs btn-danger-text" onclick="if(window.__detectionPage)window.__detectionPage.resetRegion(\'' + name + '\')" ' + (hasRegion ? '' : 'disabled ') + '>Reset</button>';
      cardsHtml += '</div></div>';
    }

    var html = '<div class="settings-page">';

    // Detection toggle
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Combat Detection</h2></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Detection Enabled</span><p class="setting-desc">Enable or disable combat detection entirely</p></div>';
    html += toggle('detection-enabled', detectionEnabled, 'if(window.__detectionPage)window.__detectionPage.saveDetection()') + '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Smart Combat Detection</span><p class="setting-desc">Use multi-signal correlation (enemy HP + damage numbers + timer)</p></div>';
    html += toggle('smart-combat-enabled', smartCombat, 'if(window.__detectionPage)window.__detectionPage.saveSmartCombat()') + '</div>';
    html += '</div></div>';

    // Detection thresholds
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Detection Thresholds</h2></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Min Enemy HP (pixels)</span><p class="setting-desc">Min pixel height to count as enemy HP bar</p></div>';
    html += '<input type="number" class="input input-sm" id="min-enemy-hp" style="width:80px" value="' + minEnemyHp + '" min="1" max="100" onchange="if(window.__detectionPage)window.__detectionPage.saveDetection()" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Min Damage Number</span><p class="setting-desc">Min damage number to count as combat signal</p></div>';
    html += '<input type="number" class="input input-sm" id="min-dmg-num" style="width:80px" value="' + minDmgNum + '" min="1" max="50" onchange="if(window.__detectionPage)window.__detectionPage.saveDetection()" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Player HP Threshold</span><p class="setting-desc">Pixel threshold for player HP bar detection</p></div>';
    html += '<input type="number" class="input input-sm" id="player-hp-threshold" style="width:80px" value="' + playerHpThreshold + '" min="1" max="500" onchange="if(window.__detectionPage)window.__detectionPage.saveDetection()" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">In-Combat Timeout (s)</span><p class="setting-desc">Seconds without signals before leaving combat state</p></div>';
    html += '<input type="number" class="input input-sm" id="incombat-timeout" style="width:80px" value="' + incombatTimeout + '" min="1" max="30" onchange="if(window.__detectionPage)window.__detectionPage.saveDetection()" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Confidence Floor</span><p class="setting-desc">Min confidence (0-1) to consider detection valid</p></div>';
    html += '<input type="number" class="input input-sm" id="confidence-floor" style="width:80px" value="' + confidenceFloor + '" min="0" max="1" step="0.05" onchange="if(window.__detectionPage)window.__detectionPage.saveDetection()" /></div>';
    html += '</div></div>';

    // Region cards
    html += '<div class="settings-section"><div class="section-header">';
    html += '<h2 class="section-title">Screen Regions</h2>';
    html += '<button class="btn btn-xs btn-secondary" onclick="if(window.__detectionPage)window.__detectionPage.validateAllRegions()">Validate All</button>';
    html += '</div><p class="section-desc" style="margin-bottom:var(--space-4)">Define screen regions for combat signal detection. Pick each region by clicking its location in the game window.</p>';
    html += '<div class="region-grid">' + cardsHtml + '</div></div>';

    html += '</div>';
    c.innerHTML = html;

    window.__detectionPage = {
      saveSmartCombat: function() {
        var el = document.getElementById('smart-combat-enabled');
        api.updateConfig({ smart_combat_detection: el ? el.checked : true }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Smart combat detection saved');
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to save smart combat setting');
          }
        });
      },
      saveDetection: function() {
        api.updateConfig({
          combat_detection_enabled: (document.getElementById('detection-enabled') || {}).checked !== false,
          smart_combat_detection: (document.getElementById('smart-combat-enabled') || {}).checked !== false,
          min_enemy_hp_pixels: parseInt((document.getElementById('min-enemy-hp') || {}).value) || 10,
          min_damage_number: parseInt((document.getElementById('min-dmg-num') || {}).value) || 1,
          player_hp_threshold: parseInt((document.getElementById('player-hp-threshold') || {}).value) || 100,
          incombat_timeout_sec: parseInt((document.getElementById('incombat-timeout') || {}).value) || 3,
          detection_confidence_floor: parseFloat((document.getElementById('confidence-floor') || {}).value) || 0.3,
        }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Detection settings saved');
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to save detection settings');
          }
        });
      },
      pickRegion: function(name) {
        if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.info('Starting region picker for: ' + name);
        api.selectRegion(name).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(name + ' region set');
            load(c);
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Region selection cancelled or failed');
          }
        });
      },
      testRegion: function(name) {
        api.resolveRegion(name).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(name + ': ' + (res.value || 'ok'));
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Test failed: ' + (res && res.message || 'unknown'));
          }
        });
      },
      validateAllRegions: function() {
        api.resolveAllRegions().then(function(res) {
          if (res && res.status === 'ok' && res.regions) {
            var rMap = {};
            for (var n = 0; n < res.regions.length; n++) {
              rMap[res.regions[n].name] = res.regions[n];
            }
            var okCount = 0;
            for (var p = 0; p < REGIONS.length; p++) {
              var rn = REGIONS[p];
              var r = rMap[rn];
              if (
                r &&
                Array.isArray(r.abs_area) &&
                r.abs_area.length === 4
              ) {
                okCount++;
              }
            }
            if (window.ShellApi && window.ShellApi.Toast) {
              if (okCount === REGIONS.length) window.ShellApi.Toast.success('All ' + REGIONS.length + ' regions valid');
              else window.ShellApi.Toast.warn(okCount + '/' + REGIONS.length + ' regions valid');
            }
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to validate regions');
          }
        }).catch(function() {
          if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to validate regions');
        });
      },
      resetRegion: function(name) {
        if (!confirm('Reset region "' + name + '"?')) return;
        api.deleteRegion(name).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(name + ' region reset');
            load(c);
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to reset region');
          }
        });
      }
    };
  } catch (err) {
    c.innerHTML = '<div class="page-error"><p>Failed to load Detection page: ' + e(err.message) + '</p></div>';
  }
}
