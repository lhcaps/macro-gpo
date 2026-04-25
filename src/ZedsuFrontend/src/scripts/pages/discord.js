// discord.js — Discord notification settings page (Phase 14.7)
// Key fixes vs old version:
// 1. All .indexOf() calls safe via asArray() from normalizers.js
// 2. Events and milestones normalized before any rendering or comparison
// 3. Webhook URL never rendered in page HTML (type=password, masked on save)
// 4. Toggle save does NOT reload the entire page
// 5. Test button disabled when no webhook configured
// 6. Cleanup function exported for page lifecycle

import * as api from '../shared/config-api.js';
import { asArray, asNumber, normalizeDiscordConfig } from '../ui/normalizers.js';

var DEFAULT_EVENTS = ['match_end', 'kill_milestone', 'combat_start', 'death', 'bot_error'];
var DEFAULT_MILESTONES = [5, 10, 20];
var _container = null;
var _currentConfig = null; // tracks in-memory state for rollback

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

function toggle(id, checked, onclick) {
  var checkedAttr = checked ? ' checked' : '';
  var onclickAttr = onclick ? ` onclick="${e(onclick)}"` : '';
  return '<label class="toggle' + (checked ? ' active' : '') + '"><input type="checkbox" id="' + e(id) + '"' + checkedAttr + onclickAttr + ' /><span class="toggle-track"></span></label>';
}

async function load(c) {
  _container = c;
  c.innerHTML = '<div class="page-loading"><div class="loading-spinner"></div></div>';

  try {
    var state = window.ShellApi ? window.ShellApi.getState() : null;
    var config = (state && state._raw && state._raw.config)
      ? state._raw.config
      : await api.getConfig();
    var discordRaw = config.discord_events || {};
    _currentConfig = normalizeDiscordConfig(discordRaw);

    var hasWebhook = _currentConfig.has_webhook;
    var activeEvents = _currentConfig.events;
    var activeMilestones = _currentConfig.kill_milestones;

    var html = '<div class="settings-page">';

    // Webhook section
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Discord Webhook</h2></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Webhook Status</span><p class="setting-desc">Discord notifications are sent via webhook URL</p></div>';
    html += '<span class="health-badge health-' + (hasWebhook ? 'ok' : 'warning') + '">' + (hasWebhook ? 'CONFIGURED' : 'NOT SET') + '</span></div>';
    html += '<div class="setting-row" style="flex-direction:column;align-items:flex-start;gap:var(--space-2)">';
    html += '<div class="setting-info"><span class="setting-label">Webhook URL</span><p class="setting-desc">' + (hasWebhook ? 'A webhook URL is configured.' : 'Paste your Discord webhook URL below.') + '</p></div>';
    html += '<div class="webhook-input-row">';
    html += '<input type="password" class="input" id="webhook-url" placeholder="https://discord.com/api/webhooks/..." style="flex:1;font-family:var(--font-mono);font-size:var(--text-xs)"' + (hasWebhook ? ' value="********************************"' : '') + '/>';
    html += '<button class="btn btn-sm btn-secondary" id="btn-save-webhook">Save</button>';
    html += '<button class="btn btn-sm btn-danger-text" id="btn-clear-webhook"' + (hasWebhook ? '' : ' disabled') + '>Clear</button>';
    html += '</div>';
    if (hasWebhook) html += '<p class="text-xs text-muted">Webhook URL is hidden for security.</p>';
    html += '</div>';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Test Webhook</span><p class="setting-desc">Send a test message to verify the webhook works</p></div>';
    html += '<button class="btn btn-sm btn-secondary" id="btn-test-webhook"' + (hasWebhook ? '' : ' disabled') + '>Send Test</button></div>';
    html += '</div></div>';

    // Events section
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Notification Events</h2><p class="section-desc">Choose which events trigger Discord notifications</p></div><div class="section-card">';
    for (var i = 0; i < DEFAULT_EVENTS.length; i++) {
      var ev = DEFAULT_EVENTS[i];
      // Safe: use asArray to normalize before indexOf
      var checked = asArray(activeEvents).indexOf(ev) >= 0;
      html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">' + eventName(ev) + '</span><p class="setting-desc">' + eventDesc(ev) + '</p></div>';
      html += toggle('event-' + ev, checked, 'window.__discordPage && window.__discordPage.saveEvents()') + '</div>';
    }
    html += '</div></div>';

    // Milestones section
    var chipValues = [1, 5, 10, 15, 20, 25, 30, 50, 100];
    var chipsHtml = '';
    for (var j = 0; j < chipValues.length; j++) {
      var n = chipValues[j];
      // Safe: activeMilestones is guaranteed number[] from normalizeDiscordConfig
      var isActive = activeMilestones.indexOf(n) >= 0;
      chipsHtml += '<button class="milestone-chip' + (isActive ? ' active' : '') + '" data-milestone="' + n + '">' + n + '</button>';
    }
    html += '<div class="settings-section"><div class="section-header"><h2 class="section-title">Kill Milestones</h2><p class="section-desc">Notify when kill count reaches these milestones</p></div><div class="section-card">';
    html += '<div class="setting-row"><div class="setting-info"><span class="setting-label">Active Milestones</span><p class="setting-desc">Click a number to toggle</p></div>';
    html += '<div class="milestone-chips">' + chipsHtml + '</div></div>';
    html += '</div></div>';

    html += '</div>';
    c.innerHTML = html;

    // Wire webhook controls
    document.getElementById('btn-save-webhook').addEventListener('click', saveWebhook);
    document.getElementById('btn-clear-webhook').addEventListener('click', clearWebhook);
    document.getElementById('btn-test-webhook').addEventListener('click', testWebhook);

    // Wire milestone chips
    var chipEls = c.querySelectorAll('.milestone-chip');
    for (var k = 0; k < chipEls.length; k++) {
      chipEls[k].addEventListener('click', (function(el) {
        var n = asNumber(el.getAttribute('data-milestone'), 0);
        toggleMilestone(n, el);
      }).bind(null, chipEls[k]));
    }

    window.__discordPage = {
      saveWebhook,
      clearWebhook,
      testWebhook,
      saveEvents,
    };
  } catch (err) {
    c.innerHTML = '<div class="page-error"><p class="text-error">Failed to load Discord page: ' + e(err.message) + '</p></div>';
  }
}

// ============================================================
// Webhook Actions
// ============================================================

function saveWebhook() {
  var urlEl = document.getElementById('webhook-url');
  if (!urlEl) return;
  var url = urlEl.value.trim();

  // If already masked/saved, no-op
  if (url.indexOf('*') >= 0 || url === '') {
    if (url === '') {
      window.ShellApi?.Toast?.error('Please enter a webhook URL');
      return;
    }
  }

  if (url && url.indexOf('https://discord.com/api/webhooks/') !== 0) {
    window.ShellApi?.Toast?.error('Invalid Discord webhook URL format');
    return;
  }

  var btn = document.getElementById('btn-save-webhook');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  api.updateDiscordConfig({ webhook_url: url }).then(function(res) {
    if (res && res.status === 'ok') {
      _currentConfig.has_webhook = true;
      if (urlEl) {
        urlEl.value = '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022';
        urlEl.type = 'password';
      }
      // Update status badge
      var badge = document.querySelector('.setting-row:first-child .health-badge');
      if (badge) { badge.textContent = 'CONFIGURED'; badge.className = 'health-badge health-ok'; }
      // Enable clear and test
      var clearBtn = document.getElementById('btn-clear-webhook');
      var testBtn = document.getElementById('btn-test-webhook');
      if (clearBtn) clearBtn.disabled = false;
      if (testBtn) testBtn.disabled = false;
      window.ShellApi?.Toast?.success('Webhook URL saved');
    } else {
      btn.disabled = false;
      btn.textContent = 'Save';
      window.ShellApi?.Toast?.error('Failed to save webhook: ' + (res && res.message || 'Check URL'));
    }
  }).catch(function(err) {
    btn.disabled = false;
    btn.textContent = 'Save';
    window.ShellApi?.Toast?.error('Failed to save webhook: ' + err.message);
  });
}

function clearWebhook() {
  if (!confirm('Remove the Discord webhook?')) return;
  var btn = document.getElementById('btn-clear-webhook');
  btn.disabled = true;
  btn.textContent = 'Clearing...';

  api.updateDiscordConfig({ webhook_url: '' }).then(function(res) {
    if (res && res.status === 'ok') {
      _currentConfig.has_webhook = false;
      var urlEl = document.getElementById('webhook-url');
      if (urlEl) { urlEl.value = ''; urlEl.type = 'text'; }
      var badge = document.querySelector('.setting-row:first-child .health-badge');
      if (badge) { badge.textContent = 'NOT SET'; badge.className = 'health-badge health-warning'; }
      var testBtn = document.getElementById('btn-test-webhook');
      if (testBtn) testBtn.disabled = true;
      btn.textContent = 'Clear';
      window.ShellApi?.Toast?.success('Webhook removed');
    } else {
      btn.disabled = false;
      btn.textContent = 'Clear';
      window.ShellApi?.Toast?.error('Failed to remove webhook');
    }
  }).catch(function(err) {
    btn.disabled = false;
    btn.textContent = 'Clear';
    window.ShellApi?.Toast?.error('Failed to remove webhook: ' + err.message);
  });
}

function testWebhook() {
  if (!_currentConfig.has_webhook) return;
  var btn = document.getElementById('btn-test-webhook');
  btn.disabled = true;
  btn.textContent = 'Sending...';

  api.testDiscordWebhook()
    .then(function(res) {
      if (res && res.status === 'ok') {
        window.ShellApi?.Toast?.success('Test message sent successfully');
      } else {
        window.ShellApi?.Toast?.error('Test failed: ' + (res && res.message || 'Check webhook URL'));
      }
    })
    .catch(function(err) {
      window.ShellApi?.Toast?.error('Test failed: ' + err.message);
    })
    .then(function() {
      if (btn) { btn.disabled = false; btn.textContent = 'Send Test'; }
    });
}

// ============================================================
// Events Toggle — saves individually without page reload
// ============================================================

function saveEvents() {
  var events = [];
  for (var k = 0; k < DEFAULT_EVENTS.length; k++) {
    var el = document.getElementById('event-' + DEFAULT_EVENTS[k]);
    if (el && el.checked) events.push(DEFAULT_EVENTS[k]);
  }
  api.updateDiscordConfig({ events: events }).then(function(res) {
    if (res && res.status === 'ok') {
      _currentConfig.events = events;
      window.ShellApi?.Toast?.success('Event settings saved');
    } else {
      // Rollback: re-render event checkboxes from saved state
      for (var i = 0; i < DEFAULT_EVENTS.length; i++) {
        var el2 = document.getElementById('event-' + DEFAULT_EVENTS[i]);
        if (el2) el2.checked = asArray(_currentConfig.events).indexOf(DEFAULT_EVENTS[i]) >= 0;
      }
      window.ShellApi?.Toast?.error('Failed to save events');
    }
  });
}

// ============================================================
// Milestones — toggles in-place without page reload
// ============================================================

function toggleMilestone(n, chipEl) {
  if (!_currentConfig.kill_milestones) _currentConfig.kill_milestones = [];
  var idx = _currentConfig.kill_milestones.indexOf(n);
  if (idx >= 0) {
    _currentConfig.kill_milestones.splice(idx, 1);
    chipEl.classList.remove('active');
  } else {
    _currentConfig.kill_milestones.push(n);
    _currentConfig.kill_milestones.sort(function(a, b) { return a - b; });
    chipEl.classList.add('active');
  }

  api.updateDiscordConfig({ kill_milestones: _currentConfig.kill_milestones }).then(function(res) {
    if (res && res.status === 'ok') {
      window.ShellApi?.Toast?.info('Milestone ' + n + (_currentConfig.kill_milestones.indexOf(n) >= 0 ? ' enabled' : ' disabled'));
    } else {
      // Rollback chip state
      var wasActive = idx < 0; // it wasn't active before the toggle
      chipEl.classList.toggle('active', wasActive);
      window.ShellApi?.Toast?.error('Failed to update milestone');
    }
  });
}

// ============================================================
// Page Lifecycle
// ============================================================

/**
 * @param {Element} target
 * @returns {{cleanup: Function}}
 */
export async function load(target) {
  await load(target);
  return { cleanup: cleanupDiscordPage };
}

export function cleanupDiscordPage() {
  window.__discordPage = null;
  _container = null;
  _currentConfig = null;
}
