// app.js — Main Zedsu app entry point
// Detects mode (hud or shell) from window label and renders the appropriate UI.

import { initHud } from './scripts/hud.js';
import { initShell } from './scripts/shell.js';

function detectMode() {
  const params = new URLSearchParams(window.location.search);
  if (params.has('hud')) return 'hud';
  if (params.has('shell')) return 'shell';
  if (window.__TAURI__) {
    try {
      const label = window.__TAURI__.window.label;
      if (label === 'hud') return 'hud';
      if (label === 'main') return 'shell';
    } catch (_) {}
  }
  return 'shell';
}

const mode = detectMode();

if (mode === 'hud') {
  document.body.setAttribute('data-mode', 'hud');
  const hudOverlay = document.getElementById('hud-overlay');
  const appShell = document.getElementById('app-shell');
  if (hudOverlay) hudOverlay.style.display = 'block';
  if (appShell) appShell.style.display = 'none';
  initHud();
} else {
  document.body.setAttribute('data-mode', 'shell');
  const hudOverlay = document.getElementById('hud-overlay');
  const appShell = document.getElementById('app-shell');
  if (hudOverlay) hudOverlay.style.display = 'none';
  if (appShell) appShell.style.display = 'flex';
  initShell();
}

// Global error handler
window.addEventListener('error', (e) => {
  console.error('[ZEDSU Shell Error]', e.error);
  window.ShellApi?.Toast?.error('Shell error: ' + (e.message || 'Unknown'));
});
