// logs.js — Backend logs viewer page

const API_BASE = 'http://localhost:9761';
var container = null;
var allLogs = [];
var pollTimer = null;
var currentFilter = 'all';

function e(s) {
  if (s === null || s === undefined) return '';
  var d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

function filterLogs() {
  if (currentFilter === 'all') return allLogs;
  return allLogs.filter(function(l) {
    var level = (l.level || 'INFO').toLowerCase();
    if (currentFilter === 'warn') return level === 'warn' || level === 'warning';
    if (currentFilter === 'error') return level === 'error' || level === 'critical';
    return level === currentFilter;
  });
}

function renderLogs() {
  var viewer = document.getElementById('logs-viewer');
  if (!viewer) return;
  var filtered = filterLogs();
  if (filtered.length === 0) {
    viewer.innerHTML = '<p class="logs-empty">No logs to display.</p>';
    return;
  }
  var html = '';
  for (var i = 0; i < filtered.length; i++) {
    var l = filtered[i];
    var level = (l.level || 'INFO').toLowerCase();
    var levelClass = level === 'error' || level === 'critical' ? 'log-error' :
                     level === 'warn' || level === 'warning' ? 'log-warn' : 'log-info';
    var time = l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : '';
    var msg = typeof l === 'string' ? l : (l.message || JSON.stringify(l));
    html += '<div class="log-line ' + levelClass + '">';
    html += '<span class="log-time">' + e(time) + '</span>';
    html += '<span class="log-level">' + (l.level || 'INFO').toUpperCase().padEnd(7) + '</span>';
    html += '<span class="log-message">' + e(msg) + '</span>';
    html += '</div>';
  }
  viewer.innerHTML = html;
  viewer.scrollTop = viewer.scrollHeight;
}

async function fetchLogs() {
  try {
    var resp = await fetch(API_BASE + '/state');
    if (!resp.ok) return;
    var data = await resp.json();
    var logs = data.logs || [];
    if (logs.length > 0) {
      allLogs = logs;
      renderLogs();
    }
  } catch (_) {}
}

export async function load(target) {
  container = target;

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
  container.innerHTML = html;

  document.getElementById('logs-copy-btn').addEventListener('click', function() {
    var filtered = filterLogs();
    var text = '';
    for (var i = 0; i < filtered.length; i++) {
      var l = filtered[i];
      text += '[' + (l.timestamp || '') + '] [' + (l.level || 'INFO') + '] ' + (typeof l === 'string' ? l : (l.message || JSON.stringify(l))) + '\n';
    }
    navigator.clipboard.writeText(text).then(function() {
      if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.success('Logs copied to clipboard');
    }).catch(function() {
      if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.error('Failed to copy logs');
    });
  });

  document.getElementById('logs-open-btn').addEventListener('click', function() {
    if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.info('Logs folder: ./logs/');
  });

  document.getElementById('logs-clear-btn').addEventListener('click', function() {
    allLogs = [];
    renderLogs();
  });

  var filterBtns = container.querySelectorAll('.filter-btn');
  for (var j = 0; j < filterBtns.length; j++) {
    (function(btn) {
      btn.addEventListener('click', function() {
        currentFilter = btn.getAttribute('data-filter');
        var allBtns = container.querySelectorAll('.filter-btn');
        for (var k = 0; k < allBtns.length; k++) allBtns[k].classList.remove('active');
        btn.classList.add('active');
        renderLogs();
      });
    })(filterBtns[j]);
  }

  await fetchLogs();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(fetchLogs, 2000);

  window.__logsPage = {
    copyLogs: function() { document.getElementById('logs-copy-btn').click(); },
    openLogsFolder: function() { if (window.ShellApi && window.ShellApi.Toast) window.ShellApi.Toast.info('Logs folder: ./logs/'); },
    clearLogs: function() { allLogs = []; renderLogs(); },
  };
}
