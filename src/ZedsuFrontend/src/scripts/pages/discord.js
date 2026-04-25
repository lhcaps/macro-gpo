// discord.js — Discord notification settings page
// Critical: webhook URL must NEVER be rendered after save.
// Uses simple string concatenation for HTML.

import * as api from '../shared/config-api.js';

var DEFAULT_EVENTS = ['match_end', 'kill_milestone', 'combat_start', 'death', 'bot_error'];
var DEFAULT_MILESTONES = [5, 10, 20];

function e(s) {
  if (s === null || s === undefined) return '';
  var d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

function eventName(ev) {
  var n = { match_end: 'Match End', kill_milestone: 'Kill Milestone', combat_start: 'Combat Start', death: 'Death', bot_error: 'Bot Error' };
  return n[ev] || ev;
}

function eventDesc(ev) {
  var d = {
    match_end: 'Notify when a match ends',
    kill_milestone: 'Notify at configured kill counts',
    combat_start: 'Notify when entering combat',
    death: 'Notify when the bot dies',
    bot_error: 'Notify on bot errors and exceptions',
  };
  return d[ev] || '';
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
    var discord = config.discord_events || {};
    var hasWebhook = (state && state.has_webhook) || discord.has_webhook || false;

    var html = '<div class="settings-page">';

    // Webhook section
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Discord Webhook</h2></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Webhook Status</span><p class="setting-desc">Discord notifications are sent via webhook URL</p></div>';
    html += '<span class="health-badge health-' + (hasWebhook ? 'ok' : 'warning') + '">' + (hasWebhook ? 'CONFIGURED' : 'NOT SET') + '</span></div>';
    html += '<div class="setting-row" style="flex-direction:column;align-items:flex-start;gap:var(--space-2)">';
    html += '<div class="setting-info"><span class="setting-label">Webhook URL</span><p class="setting-desc">' + (hasWebhook ? 'A webhook URL is configured.' : 'Paste your Discord webhook URL below.') + '</p></div>';
    html += '<div class="webhook-input-row">';
    html += '<input type="password" class="input" id="webhook-url" placeholder="https://discord.com/api/webhooks/..." style="flex:1;font-family:var(--font-mono);font-size:var(--text-xs)" ' + (hasWebhook ? 'value="**************" ' : '') + '/>';
    html += '<button class="btn btn-sm btn-secondary" onclick="if(window.__discordPage)window.__discordPage.saveWebhook()">Save</button>';
    html += '<button class="btn btn-sm btn-danger-text" onclick="if(window.__discordPage)window.__discordPage.clearWebhook()" ' + (hasWebhook ? '' : 'disabled ') + '>Clear</button>';
    html += '</div>';
    if (hasWebhook) html += '<p class="text-xs text-muted">Webhook URL is hidden for security.</p>';
    html += '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Test Webhook</span><p class="setting-desc">Send a test message to verify the webhook works</p></div>';
    html += '<button class="btn btn-sm btn-secondary" id="test-webhook-btn" onclick="if(window.__discordPage)window.__discordPage.testWebhook()" ' + (hasWebhook ? '' : 'disabled ') + '>Send Test</button></div>';
    html += '</div></div>';

    // Events section
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Notification Events</h2><p class="section-desc">Choose which events trigger Discord notifications</p></div><div class="section-card">';
    for (var i = 0; i < DEFAULT_EVENTS.length; i++) {
      var ev = DEFAULT_EVENTS[i];
      var checked = (discord.events || []).indexOf(ev) >= 0;
      html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">' + eventName(ev) + '</span><p class="setting-desc">' + eventDesc(ev) + '</p></div>';
      html += toggle('event-' + ev, checked, 'if(window.__discordPage)window.__discordPage.saveEvents()') + '</div>';
    }
    html += '</div></div>';

    // Milestones section
    var activeMilestones = discord.kill_milestones || DEFAULT_MILESTONES;
    var chipsHtml = '';
    var chipValues = [1, 5, 10, 15, 20, 25, 30, 50, 100];
    for (var j = 0; j < chipValues.length; j++) {
      var n = chipValues[j];
      var isActive = activeMilestones.indexOf(n) >= 0;
      chipsHtml += '<button class="milestone-chip' + (isActive ? ' active' : '') + '" onclick="if(window.__discordPage)window.__discordPage.toggleMilestone(' + n + ')">' + n + '</button>';
    }
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Kill Milestones</h2><p class="section-desc">Notify when kill count reaches these milestones</p></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Active Milestones</span><p class="setting-desc">Click a number to toggle. Current: ' + activeMilestones.join(', ') + '</p></div>';
    html += '<div class="milestone-chips">' + chipsHtml + '</div></div>';
    html += '</div></div>';

    html += '</div>';
    c.innerHTML = html;

    var activeM = activeMilestones.slice();

    window.__discordPage = {
      saveWebhook: function() {
        var urlEl = document.getElementById('webhook-url');
        var url = urlEl ? urlEl.value.trim() : '';
        if (!url) {
          if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Please enter a webhook URL');
          return;
        }
        if (url.indexOf('https://discord.com/api/webhooks/') !== 0) {
          if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Invalid Discord webhook URL format');
          return;
        }
        api.updateDiscordConfig({ webhook_url: url }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Webhook URL saved');
            if (urlEl) {
              urlEl.value = '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022';
              urlEl.type = 'password';
            }
            load(c);
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to save webhook: ' + (res && res.message || 'Check URL'));
          }
        });
      },
      clearWebhook: function() {
        if (!confirm('Remove the Discord webhook?')) return;
        api.updateDiscordConfig({ webhook_url: '' }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Webhook removed');
            load(c);
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to remove webhook');
          }
        });
      },
      testWebhook: function() {
        var btn = document.getElementById('test-webhook-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Sending...'; }
        api.testDiscordWebhook()
          .then(function(res) {
            if (res && res.status === 'ok') {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success(res.sent ? 'Test message sent successfully' : 'Webhook not configured');
            } else {
              if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Test failed: ' + (res && res.message || 'Check webhook URL'));
            }
          })
          .catch(function(err) {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Test failed: ' + err.message);
          })
          .then(function() {
            if (btn) { btn.disabled = false; btn.textContent = 'Send Test'; }
          });
      },
      saveEvents: function() {
        var events = [];
        for (var k = 0; k < DEFAULT_EVENTS.length; k++) {
          var el = document.getElementById('event-' + DEFAULT_EVENTS[k]);
          if (el && el.checked) events.push(DEFAULT_EVENTS[k]);
        }
        api.updateDiscordConfig({ events: events }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Event settings saved');
          } else {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to save events');
          }
        });
      },
      toggleMilestone: function(n) {
        var idx = activeM.indexOf(n);
        if (idx >= 0) activeM.splice(idx, 1);
        else activeM.push(n);
        activeM.sort(function(a, b) { return a - b; });
        var chipEls = c.querySelectorAll('.milestone-chip');
        for (var m = 0; m < chipEls.length; m++) {
          var v = parseInt(chipEls[m].textContent);
          chipEls[m].classList.toggle('active', activeM.indexOf(v) >= 0);
        }
        api.updateDiscordConfig({ kill_milestones: activeM }).then(function(res) {
          if (res && res.status === 'ok') {
            if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.info('Milestone ' + n + (activeM.indexOf(n) >= 0 ? ' enabled' : ' disabled'));
          }
        });
      }
    };
  } catch (err) {
    c.innerHTML = '<div class="page-error"><p>Failed to load Discord page: ' + e(err.message) + '</p></div>';
  }
}
