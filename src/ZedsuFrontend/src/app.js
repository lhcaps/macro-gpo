// app.js — Main Zedsu app entry point (Phase 13-06 enhanced)
// Detects mode (hud or shell) from window label and renders the appropriate UI.

import { initHud } from './scripts/hud.js';
import { initShell } from './scripts/shell.js';
import Toast from './scripts/toast.js';
import Confirm from './scripts/confirm.js';

function detectMode() {
  var params = new URLSearchParams(window.location.search);
  if (params.has('hud')) return 'hud';
  if (params.has('shell')) return 'shell';
  if (window.__TAURI__) {
    try {
      var label = window.__TAURI__.window.label;
      if (label === 'hud') return 'hud';
      if (label === 'main') return 'shell';
    } catch (e) {}
  }
  return 'shell';
}

var mode = detectMode();

if (mode === 'hud') {
  document.body.setAttribute('data-mode', 'hud');
  var hudOverlay = document.getElementById('hud-overlay');
  var appShell = document.getElementById('app-shell');
  if (hudOverlay) hudOverlay.style.display = 'block';
  if (appShell) appShell.style.display = 'none';
  initHud();
} else {
  document.body.setAttribute('data-mode', 'shell');
  var hudOverlay2 = document.getElementById('hud-overlay');
  var appShell2 = document.getElementById('app-shell');
  if (hudOverlay2) hudOverlay2.style.display = 'none';
  if (appShell2) appShell2.style.display = 'flex';
  initShell();
}

// Error boundary — catches unhandled errors and shows toast
window.addEventListener('error', function(e) {
  console.error('[ZEDSU Shell Error]', e.error);
  if (window.ToastApi) {
    window.ToastApi.error('Shell error: ' + (e.message || 'Unknown'));
  }
});

window.addEventListener('unhandledrejection', function(e) {
  console.error('[ZEDSU Unhandled Rejection]', e.reason);
  if (window.ToastApi) {
    window.ToastApi.error('Unhandled error: ' + (e.reason && e.reason.message ? e.reason.message : e.reason));
  }
});

// Global APIs exposed for Tauri/Rust commands
window.ToastApi = {
  success: function(msg, opts) { Toast.success(msg, opts); },
  error: function(msg, opts) { Toast.error(msg, opts); },
  warning: function(msg, opts) { Toast.warning(msg, opts); },
  info: function(msg, opts) { Toast.info(msg, opts); },
};

window.ConfirmApi = {
  show: function(opts) { return Confirm.show(opts); },
};
