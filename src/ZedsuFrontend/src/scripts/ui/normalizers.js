// normalizers.js — Safe type coercion utilities for Zedsu frontend
// All page modules MUST use these before rendering or comparing backend data.
// This prevents crashes like "indexOf is not a function" on malformed config.

/**
 * Coerce value to array. Returns [] for undefined, null, object, string, number.
 * @param {*} value
 * @returns {Array}
 */
export function asArray(value) {
  if (value == null) return [];
  if (Array.isArray(value)) return value;
  return [];
}

/**
 * Coerce value to boolean.
 * @param {*} value
 * @returns {boolean}
 */
export function asBool(value) {
  if (value == null) return false;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    const lower = value.toLowerCase();
    return lower === 'true' || lower === '1' || lower === 'yes';
  }
  return Boolean(value);
}

/**
 * Coerce value to number.
 * @param {*} value
 * @param {number} [fallback=0]
 * @returns {number}
 */
export function asNumber(value, fallback = 0) {
  if (value == null) return fallback;
  if (typeof value === 'number' && isFinite(value)) return value;
  const parsed = parseFloat(value);
  return isFinite(parsed) ? parsed : fallback;
}

/**
 * Normalize discord_events config section.
 * @param {object} discord
 * @returns {{has_webhook: boolean, events: string[], kill_milestones: number[]}}
 */
export function normalizeDiscordConfig(discord) {
  if (!discord || typeof discord !== 'object') {
    return { has_webhook: false, events: [], kill_milestones: [5, 10, 20] };
  }
  const events = asArray(discord.events).filter(ev => typeof ev === 'string' && ev.length > 0);
  const milestones = asArray(discord.kill_milestones)
    .map(n => asNumber(n, -1))
    .filter(n => n > 0);
  return {
    has_webhook: asBool(discord.has_webhook),
    events,
    kill_milestones: milestones.length > 0 ? milestones : [5, 10, 20],
  };
}

/**
 * Normalize runtime config section.
 * @param {object} runtime
 * @returns {{window_title: string, auto_focus: boolean, require_focus: boolean, scan_interval: number, move_interval: number}}
 */
export function normalizeRuntimeConfig(runtime) {
  if (!runtime || typeof runtime !== 'object') {
    return { window_title: '', auto_focus: false, require_focus: true, scan_interval: 200, move_interval: 100 };
  }
  return {
    window_title: String(runtime.window_title || ''),
    auto_focus: asBool(runtime.auto_focus),
    require_focus: asBool(runtime.require_focus),
    scan_interval: asNumber(runtime.scan_interval, 200),
    move_interval: asNumber(runtime.move_interval, 100),
  };
}

/**
 * Normalize YOLO model state.
 * @param {object} yolo
 * @returns {{available: boolean, model_path: string|null, quality_score: number|null}}
 */
export function normalizeYoloState(yolo) {
  if (!yolo || typeof yolo !== 'object') {
    return { available: false, model_path: null, quality_score: null };
  }
  return {
    available: asBool(yolo.available),
    model_path: yolo.model_path || yolo.active_model || null,
    quality_score: asNumber(yolo.quality_score, null),
  };
}

/**
 * Normalize logs array.
 * @param {*} logs - raw logs from backend
 * @returns {Array<{timestamp: string, level: string, message: string}>}
 */
export function normalizeLogs(logs) {
  const arr = asArray(logs);
  return arr.map(l => {
    if (typeof l === 'string') {
      return { timestamp: '', level: 'info', message: l };
    }
    return {
      timestamp: String(l.timestamp || ''),
      level: String(l.level || 'INFO').toUpperCase(),
      message: String(l.message || JSON.stringify(l)),
    };
  });
}
