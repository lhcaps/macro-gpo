// config-api.js — Shared backend API helpers for all settings pages
// CRITICAL: All commands use { action, payload } format per backend contract

const API_BASE = 'http://localhost:9761';

// ============================================================
// Base command helper
// ============================================================
async function postCommand(action, payload = null) {
  try {
    const body = payload !== null ? { action, payload } : { action };
    const resp = await fetch(`${API_BASE}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (data.status === 'error') throw new Error(data.message || 'Command failed');
    return data;
  } catch (err) {
    throw err;
  }
}

// ============================================================
// Config — /state has config, /command has get/set handlers
// ============================================================

export async function getConfig() {
  const resp = await fetch(`${API_BASE}/state`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();
  return data.config || {};
}

export async function updateConfig(updates) {
  return postCommand('update_config', updates);
}

// ============================================================
// Region — pick via select_region, resolve via resolve_region / resolve_all_regions
// ============================================================

export async function getRegions() {
  const data = await postCommand('get_regions');
  return data.regions || [];
}

export async function setRegion(name, region) {
  return postCommand('set_region', { name, ...region });
}

export async function selectRegion(name) {
  return postCommand('select_region', { name });
}

export async function resolveRegion(name) {
  return postCommand('resolve_region', { name });
}

export async function resolveAllRegions() {
  return postCommand('resolve_all_regions');
}

export async function deleteRegion(name) {
  return postCommand('delete_region', { name });
}

// ============================================================
// Positions — fetch via /command, NOT from /state
// ============================================================

export async function getPositions() {
  const data = await postCommand('get_positions');
  return data.positions || [];
}

export async function setPosition(name, position) {
  return postCommand('set_position', { name, ...position });
}

export async function resolvePosition(name) {
  return postCommand('resolve_position', { name });
}

export async function deletePosition(name) {
  return postCommand('delete_position', { name });
}

// ============================================================
// Discord — webhook managed by backend, URL never sent to frontend
// ============================================================

export async function testDiscordWebhook() {
  // Takes NO arguments — backend reads saved URL internally
  return postCommand('test_discord_webhook');
}

export async function updateDiscordConfig(updates) {
  return postCommand('update_config', { discord_events: updates });
}

// ============================================================
// YOLO commands
// ============================================================

export async function sendYoloCommand(cmd, params = {}) {
  return postCommand(cmd, params);
}

// ============================================================
// Utility
// ============================================================

export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}
