// combat-ai.js — Combat AI settings page (Phase 12.5 telemetry exposed)
// Uses simple string concatenation for HTML.

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
    var combat = (state && state._raw) ? (state._raw.combat || {}) : {};
    var aiConfig = config.combat_ai || {};

    var intent = combat.intent || '—';
    var crowdRisk = combat.crowd_risk;
    var crowdDisplay = (crowdRisk !== null && crowdRisk !== undefined) ? crowdRisk.toFixed(2) : '—';
    var deathReason = combat.death_reason || '—';
    var visEnemies = (combat.visible_enemy_count !== undefined ? combat.visible_enemy_count : (combat.visible_enemies !== undefined ? combat.visible_enemies : '—'));
    var targetCount = (aiConfig.target_memory_enabled && combat.target_count !== undefined) ? combat.target_count : null;

    var crowdThreshold = aiConfig.crowd_risk_threshold !== undefined ? aiConfig.crowd_risk_threshold : 0.5;
    var crowdThresholdDisplay = crowdThreshold.toFixed(2);

    var html = '<div class="settings-page">';

    // Status card
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Combat AI Status</h2></div><div class="section-card">';
    html += '<div class="metric-row"><span class="metric-label">Current Intent</span><span class="metric-value font-mono text-ai">' + e(intent) + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Crowd Risk</span><span class="metric-value font-mono">' + crowdDisplay + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Target Memory</span><span class="metric-value">' + (aiConfig.target_memory_enabled && targetCount !== null ? targetCount + ' targets' : '—') + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Last Death Reason</span><span class="metric-value text-error">' + e(deathReason) + '</span></div>';
    html += '<div class="metric-row"><span class="metric-label">Visible Enemies</span><span class="metric-value font-mono">' + visEnemies + '</span></div>';
    html += '</div></div>';

    // Telemetry
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Telemetry</h2><p class="section-desc">Run recording and death analysis (Phase 12.5 feature)</p></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Enable Telemetry</span><p class="setting-desc">Record combat decisions and outcomes for analysis</p></div>';
    html += toggle('ai-telemetry-enabled', aiConfig.telemetry_enabled, 'if(window.__combatAiPage)window.__combatAiPage.save(\'telemetry\')') + '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Snapshot on Death</span><p class="setting-desc">Save a telemetry snapshot when the bot dies</p></div>';
    html += toggle('ai-snapshot-death', aiConfig.snapshot_on_death, 'if(window.__combatAiPage)window.__combatAiPage.save(\'telemetry\')') + '</div>';
    html += '</div></div>';

    // Target Memory
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Target Memory</h2><p class="section-desc">How long the AI remembers enemy targets after losing sight</p></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Enable Target Memory</span><p class="setting-desc">Track enemies even when temporarily not visible</p></div>';
    html += toggle('ai-target-mem-enabled', aiConfig.target_memory_enabled, 'if(window.__combatAiPage)window.__combatAiPage.save(\'target_memory\')') + '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Lost Grace (seconds)</span><p class="setting-desc">How long to remember a lost target</p></div>';
    html += '<input type="number" class="input input-sm" id="ai-lost-grace" style="width:80px" value="' + (aiConfig.target_lost_grace_sec || 3) + '" min="1" max="30" onchange="if(window.__combatAiPage)window.__combatAiPage.save(\'target_memory\')" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Switch Penalty</span><p class="setting-desc">Penalty for switching targets too often (0-10)</p></div>';
    html += '<input type="number" class="input input-sm" id="ai-switch-penalty" style="width:80px" value="' + (aiConfig.target_switch_penalty || 2) + '" min="0" max="10" step="0.5" onchange="if(window.__combatAiPage)window.__combatAiPage.save(\'target_memory\')" /></div>';
    html += '</div></div>';

    // Situation Model
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Situation Model</h2><p class="section-desc">AI threat assessment and crowd awareness parameters</p></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Crowd Risk Threshold</span><p class="setting-desc">Crowd risk level at which AI adjusts behavior (0.0-1.0)</p></div>';
    html += '<div class="setting-control">';
    html += '<input type="range" class="range-input" id="ai-crowd-threshold" min="0" max="1" step="0.05" value="' + crowdThreshold + '" oninput="var el=document.getElementById(\'crowd-threshold-value\');if(el)el.textContent=parseFloat(this.value).toFixed(2)" onchange="if(window.__combatAiPage)window.__combatAiPage.save(\'situation_model\')" />';
    html += '<span class="range-value font-mono" id="crowd-threshold-value">' + crowdThresholdDisplay + '</span>';
    html += '</div></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Nearby Enemy Crowd Count</span><p class="setting-desc">Min enemies nearby to trigger crowd behavior</p></div>';
    html += '<input type="number" class="input input-sm" id="ai-nearby-crowd" style="width:80px" value="' + (aiConfig.nearby_enemy_crowd_count || 2) + '" min="1" max="10" onchange="if(window.__combatAiPage)window.__combatAiPage.save(\'situation_model\')" /></div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Visible Enemy Crowd Count</span><p class="setting-desc">Min visible enemies to trigger crowd behavior</p></div>';
    html += '<input type="number" class="input input-sm" id="ai-visible-crowd" style="width:80px" value="' + (aiConfig.visible_enemy_crowd_count || 1) + '" min="1" max="10" onchange="if(window.__combatAiPage)window.__combatAiPage.save(\'situation_model\')" /></div>';
    html += '</div></div>';

    // Movement Policy
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Movement Policy</h2><p class="section-desc">AI movement decision making</p></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Scored Fallback</span><p class="setting-desc">Use scored movement instead of random fallback</p></div>';
    html += toggle('ai-scored-fallback', aiConfig.random_movement_fallback !== false, 'if(window.__combatAiPage)window.__combatAiPage.save(\'movement_policy\')') + '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Repeated Action Penalty</span><p class="setting-desc">Penalty for repeating the same action (0-10)</p></div>';
    html += '<input type="number" class="input input-sm" id="ai-repeat-penalty" style="width:80px" value="' + (aiConfig.repeated_action_penalty || 0.15) + '" min="0" max="10" step="0.05" onchange="if(window.__combatAiPage)window.__combatAiPage.save(\'movement_policy\')" /></div>';
    html += '</div></div>';

    // Death Classifier
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Death Classifier</h2><p class="section-desc">Analyze and classify death events (Phase 12.5 feature)</p></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Enable Death Classifier</span><p class="setting-desc">Analyze screen to determine cause of death</p></div>';
    var deathClsEnabled = aiConfig.death_classifier_enabled !== false;
    html += toggle('ai-death-classifier-enabled', deathClsEnabled, 'if(window.__combatAiPage)window.__combatAiPage.save(\'death_classifier\')') + '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Last Death Reason</span><p class="setting-desc">Most recent classified death cause</p></div>';
    html += '<span class="metric-value text-error font-mono">' + e(deathReason) + '</span></div>';
    html += '</div></div>';

    html += '</div>';
    c.innerHTML = html;

    window.__combatAiPage = {
      save: function(section) {
        var updates = {};
        if (section === 'telemetry') {
          updates = {
            telemetry_enabled: (document.getElementById('ai-telemetry-enabled') || {}).checked || false,
            snapshot_on_death: (document.getElementById('ai-snapshot-death') || {}).checked || false,
          };
        } else if (section === 'target_memory') {
          updates = {
            target_memory_enabled: (document.getElementById('ai-target-mem-enabled') || {}).checked || false,
            target_lost_grace_sec: parseFloat((document.getElementById('ai-lost-grace') || {}).value) || 3,
            target_switch_penalty: parseFloat((document.getElementById('ai-switch-penalty') || {}).value) || 2,
          };
        } else if (section === 'situation_model') {
          updates = {
            crowd_risk_threshold: parseFloat((document.getElementById('ai-crowd-threshold') || {}).value) || 0.5,
            nearby_enemy_crowd_count: parseInt((document.getElementById('ai-nearby-crowd') || {}).value) || 2,
            visible_enemy_crowd_count: parseInt((document.getElementById('ai-visible-crowd') || {}).value) || 1,
          };
        } else if (section === 'movement_policy') {
          updates = {
            random_movement_fallback: (document.getElementById('ai-scored-fallback') || {}).checked || false,
            repeated_action_penalty: parseFloat((document.getElementById('ai-repeat-penalty') || {}).value) || 0.15,
          };
        } else if (section === 'death_classifier') {
          updates = {
            death_classifier_enabled: (document.getElementById('ai-death-classifier-enabled') || {}).checked || false,
          };
        }
        api.updateConfig({ combat_ai: updates }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(section + ' settings saved');
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to save: ' + (res && res.message || 'unknown'));
          }
        });
      }
    };
  } catch (err) {
    c.innerHTML = '<div class="page-error"><p>Failed to load Combat AI page: ' + e(err.message) + '</p></div>';
  }
}
