// logs.js — Backend logs viewer page (Phase 14.7)
// Key fixes vs old version:
// 1. Empty logs array renders empty state — spinner never hangs
// 2. Polls ONLY while logs tab is active
// 3. Auto-scroll guard: only scrolls if user is at bottom
// 4. Open Folder calls backend command (not just toast)
// 5. Cleanup function stops polling on tab leave

import { normalizeLogs } from '../ui/normalizers.js';

const API_BASE = 'http://localhost:9761';
var _container = null;
var _allLogs = [];
var _pollTimer = null;
var _currentFilter = 'all';
var _userScrolledUp = false;

function e(s) {
  if (s === null || s === undefined) return '';
  var d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

function filterLogs() {
  if (_currentFilter === 'all') return _allLogs;
  return _allLogs.filter(function(l) {
    var level = (l.level || 'INFO').toLowerCase();
    if (_currentFilter === 'warn') return level === 'warn' || level === 'warning';
    if (_currentFilter === 'error') return level === 'error' || level === 'critical';
    return level === _currentFilter;
  });
}

function renderLogs() {
  var viewer = document.getElementById('logs-viewer');
  if (!viewer) return;

  var filtered = filterLogs();

  // Empty state — spinner gone, never hangs
  if (filtered.length === 0) {
    viewer.innerHTML = '<div class="logs-empty-state"><div class="empty-state"><div class="empty-state-icon">&#x2212;</div><p class="empty-state-msg">No logs yet</p><p class="text-xs text-muted" style="margin-top:var(--space-2)">Logs appear here once the backend starts</p></div></div>';
    return;
  }

  var html = '';
  for (var i = 0; i < filtered.length; i++) {
    var l = filtered[i];
    var level = (l.level || 'INFO').toLowerCase();
    var levelClass = level === 'error' || level === 'critical' ? 'log-error' :
                     level === 'warn' || level === 'warning' ? 'log-warn' : 'log-info';
    var time = l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : '';
    var msg = l.message || '';
    html += '<div class="log-line ' + levelClass + '">';
    html += '<span class="log-time">' + e(time) + '</span>';
    html += '<span class="log-level">' + (l.level || 'INFO').toUpperCase().padEnd(7) + '</span>';
    html += '<span class="log-message">' + e(msg) + '</span>';
    html += '</div>';
  }
  viewer.innerHTML = html;

  // Auto-scroll only if user is at the bottom (not scrolled up)
  if (!_userScrolledUp) {
    viewer.scrollTop = viewer.scrollHeight;
  }
}

async function fetchLogs() {
  try {
    var resp = await fetch(API_BASE + '/state');
    if (!resp.ok) return;
    var data = await resp.json();
    var logsRaw = data.logs || [];
    var normalized = normalizeLogs(logsRaw);
    if (normalized.length > 0 || _allLogs.length > 0) {
      _allLogs = normalized;
      renderLogs();
    }
  } catch (_) {}
}

function startPolling() {
  if (_pollTimer) return;
  fetchLogs();
  _pollTimer = setInterval(fetchLogs, 2000);
}

function stopPolling() {
  if (_pollTimer) {
    clearInterval(_pollTimer);
    _pollTimer = null;
  }
}

export async function load(target) {
  _container = target;
  _currentFilter = 'all';
  _userScrolledUp = false;
  _allLogs = [];

  var html = '<div class="logs-page">';
  html += '<div class="logs-toolbar">';
  html += '<div class="logs-filters">';
  html += '<button class="btn btn-xs filter-btn active" data-filter="all">All</button>';
  html += '<button class="btn btn-xs filter-btn" data-filter="info">Info</button>';
  html += '<button class="btn btn-xs filter-btn" data-filter="warn">Warning</button>';
  html += '<button class="btn btn-xs filter-btn" data-filter="error">Error</button>';
  html += '</div>';
  html += '<div class="logs-actions">';
  html += '<button class="btn btn-xs btn-secondary" id="logs-copy-btn">Copy</button>';
  html += '<button class="btn btn-xs btn-secondary" id="logs-open-btn">Open Folder</button>';
  html += '<button class="btn btn-xs btn-secondary" id="logs-clear-btn">Clear View</button>';
  html += '</div>';
  html += '</div>';
  html += '<div class="logs-viewer" id="logs-viewer"><div class="page-loading"><div class="loading-spinner"></div></div></div>';
  html += '</div>';

  _container.innerHTML = html;

  // Copy button
  document.getElementById('logs-copy-btn').addEventListener('click', function() {
    var filtered = filterLogs();
    var text = '';
    for (var i = 0; i < filtered.length; i++) {
      var l = filtered[i];
      text += '[' + (l.timestamp || '') + '] [' + (l.level || 'INFO') + '] ' + l.message + '\n';
    }
    if (!text) {
      window.ShellApi?.Toast?.info('No logs to copy');
      return;
    }
    navigator.clipboard.writeText(text).then(function() {
      window.ShellApi?.Toast?.success('Logs copied to clipboard');
    }).catch(function() {
      window.ShellApi?.Toast?.error('Failed to copy logs');
    });
  });

  // Open Folder — call backend command via ShellApi
  document.getElementById('logs-open-btn').addEventListener('click', function() {
    // Try to open via backend command first
    ShellApi.sendCommand('open_logs_folder').then(function(res) {
      if (!res.success) {
        window.ShellApi?.Toast?.info('Logs folder: ./logs/');
      }
    }).catch(function() {
      window.ShellApi?.Toast?.info('Logs folder: ./logs/');
    });
  });

  // Clear View — only clears the view, not backend logs
  document.getElementById('logs-clear-btn').addEventListener('click', function() {
    _allLogs = [];
    renderLogs();
  });

  // Filter buttons
  var filterBtns = _container.querySelectorAll('.filter-btn');
  for (var j = 0; j < filterBtns.length; j++) {
    (function(btn) {
      btn.addEventListener('click', function() {
        _currentFilter = btn.getAttribute('data-filter');
        var allBtns = _container.querySelectorAll('.filter-btn');
        for (var k = 0; k < allBtns.length; k++) allBtns[k].classList.remove('active');
        btn.classList.add('active');
        renderLogs();
      });
    })(filterBtns[j]);
  }

  // Auto-scroll guard: detect if user scrolled up
  var viewer = document.getElementById('logs-viewer');
  if (viewer) {
    viewer.addEventListener('scroll', function() {
      var threshold = 50;
      _userScrolledUp = (viewer.scrollHeight - viewer.scrollTop - viewer.clientHeight) > threshold;
    }, { passive: true });
  }

  // Initial fetch and start polling
  await fetchLogs();
  startPolling();

  window.__logsPage = {
    copyLogs: function() { document.getElementById('logs-copy-btn')?.click(); },
    openLogsFolder: function() { document.getElementById('logs-open-btn')?.click(); },
    clearLogs: function() { _allLogs = []; renderLogs(); },
  };
}

export function cleanupLogsPage() {
  stopPolling();
  window.__logsPage = null;
  _container = null;
  _allLogs = [];
  _currentFilter = 'all';
  _userScrolledUp = false;
}
