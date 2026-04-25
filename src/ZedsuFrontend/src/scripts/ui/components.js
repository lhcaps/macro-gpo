// components.js — Reusable UI component builders for Zedsu frontend
// Vanilla JS — no npm. All components return HTML string or DOM builder function.
// Design tokens used from tokens.css variables.

import Toast from '../toast.js';

/**
 * Escape HTML to prevent XSS. Used by all string-based HTML builders.
 * @param {*} s
 * @returns {string}
 */
export function e(s) {
  if (s === null || s === undefined) return '';
  const d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

/**
 * Truncate a string to maxLen chars, appending '...' if truncated.
 * @param {string} str
 * @param {number} maxLen
 * @returns {string}
 */
export function truncate(str, maxLen) {
  if (!str) return '';
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 1) + '\u2026';
}

/**
 * Status badge — colored pill for boolean/status indicators.
 * @param {object} opts
 * @param {string} opts.text
 * @param {'ok'|'warning'|'error'|'info'|'muted'} opts.variant
 * @param {string} [opts.title] - tooltip text
 * @returns {string} HTML
 */
export function StatusBadge({ text, variant = 'muted', title = '' }) {
  const titleAttr = title ? ` title="${e(title)}"` : '';
  return `<span class="health-badge health-${variant}"${titleAttr}>${e(text)}</span>`;
}

/**
 * Action button.
 * @param {object} opts
 * @param {string} opts.label
 * @param {string} [opts.variant='secondary'] - primary | secondary | danger | ghost
 * @param {string} [opts.size='sm'] - xs | sm | md | lg
 * @param {string} [opts.id]
 * @param {string} [opts.onclick]
 * @param {boolean} [opts.disabled]
 * @returns {string} HTML
 */
export function Button({ label, variant = 'secondary', size = 'sm', id = '', onclick = '', disabled = false }) {
  const idAttr = id ? ` id="${e(id)}"` : '';
  const disabledAttr = disabled ? ' disabled' : '';
  const onclickAttr = onclick ? ` onclick="${e(onclick)}"` : '';
  const sizeClass = size !== 'sm' ? ` btn-${size}` : '';
  return `<button class="btn btn-${variant}${sizeClass}"${idAttr}${onclickAttr}${disabledAttr}>${e(label)}</button>`;
}

/**
 * Toggle switch for boolean settings.
 * @param {object} opts
 * @param {string} opts.id
 * @param {boolean} opts.checked
 * @param {string} [opts.onchange]
 * @param {boolean} [opts.disabled]
 * @returns {string} HTML
 */
export function Toggle({ id, checked, onchange = '', disabled = false }) {
  const checkedAttr = checked ? ' checked' : '';
  const disabledAttr = disabled ? ' disabled' : '';
  const onclickAttr = onchange ? ` onclick="${e(onchange)}"` : '';
  return `<label class="toggle${checked ? ' active' : ''}"${id ? ` id="${e(id)}-toggle"` : ''}><input type="checkbox" id="${e(id)}"${checkedAttr}${disabledAttr} onchange="${e(onchange)}" /><span class="toggle-track"></span></label>`;
}

/**
 * Metric row — label + value pair in a row.
 * @param {object} opts
 * @param {string} opts.label
 * @param {string|number} opts.value
 * @param {string} [opts.valueClass]
 * @param {string} [opts.title] - tooltip
 * @returns {string} HTML
 */
export function MetricRow({ label, value, valueClass = '', title = '' }) {
  const titleAttr = title ? ` title="${e(title)}"` : '';
  const valueClassAttr = valueClass ? ` class="${e(valueClass)}"` : '';
  return `<div class="metric-row"><span class="metric-label">${e(label)}</span><span${valueClassAttr}${titleAttr}>${e(String(value ?? '\u2014'))}</span></div>`;
}

/**
 * Card container.
 * @param {object} opts
 * @param {string} opts.title
 * @param {string} opts.body - HTML content
 * @param {string} [opts.footer] - HTML content for footer
 * @param {string} [opts.icon] - unicode icon character
 * @param {string} [opts.id]
 * @returns {string} HTML
 */
export function Card({ title, body, footer = '', icon = '', id = '' }) {
  const idAttr = id ? ` id="${e(id)}"` : '';
  const iconEl = icon ? `<span class="metric-card-icon">${icon}</span>` : '';
  const footerEl = footer ? `<div class="metric-card-footer">${footer}</div>` : '';
  return `<div class="metric-card"${idAttr}><div class="metric-card-header">${iconEl}<h3 class="metric-card-title">${e(title)}</h3></div><div class="metric-card-body">${body}</div>${footerEl}</div>`;
}

/**
 * Section with header and card body.
 * @param {object} opts
 * @param {string} opts.title
 * @param {string} [opts.desc]
 * @param {string} opts.content - HTML content
 * @param {string} [opts.id]
 * @returns {string} HTML
 */
export function Section({ title, desc = '', content, id = '' }) {
  const idAttr = id ? ` id="${e(id)}"` : '';
  const descEl = desc ? `<p class="section-desc">${e(desc)}</p>` : '';
  return `<div class="settings-section"${idAttr}><div class="section-header"><h2 class="section-title">${e(title)}</h2>${descEl}</div><div class="section-card">${content}</div></div>`;
}

/**
 * Empty state — shown when a list/collection has no items.
 * @param {object} opts
 * @param {string} opts.message
 * @param {string} [opts.hint]
 * @returns {string} HTML
 */
export function EmptyState({ message, hint = '' }) {
  const hintEl = hint ? `<p class="text-muted text-sm">${e(hint)}</p>` : '';
  return `<div class="empty-state"><div class="empty-state-icon">&#x2212;</div><p class="empty-state-msg">${e(message)}</p>${hintEl}</div>`;
}

/**
 * Error state — shown when a page fetch fails.
 * @param {object} opts
 * @param {string} opts.message
 * @param {Function} [opts.onRetry] - JS expression string to call on retry
 * @returns {string} HTML
 */
export function ErrorState({ message, onRetry = '' }) {
  const retryBtn = onRetry ? `<button class="btn btn-secondary btn-sm" onclick="${e(onRetry)}">Retry</button>` : '';
  return `<div class="page-error"><p class="text-error">${e(message)}</p>${retryBtn ? '<div style="margin-top:var(--space-3)">' + retryBtn + '</div>' : ''}</div>`;
}

/**
 * Toolbar — filter + action buttons row.
 * @param {object} opts
 * @param {Array<{label: string, filter: string, active?: boolean}>} opts.filters
 * @param {Array<{label: string, id: string, onclick?: string}>} opts.actions
 * @param {string} [opts.extra] - extra HTML to inject
 * @returns {string} HTML
 */
export function Toolbar({ filters = [], actions = [], extra = '' }) {
  let html = '<div class="logs-toolbar"><div class="logs-filters">';
  for (const f of filters) {
    const active = f.active !== false ? ' active' : '';
    html += `<button class="btn btn-xs filter-btn${active}" data-filter="${e(f.filter)}">${e(f.label)}</button>`;
  }
  html += '</div><div class="logs-actions">';
  if (extra) html += extra;
  for (const a of actions) {
    const onclick = a.onclick ? ` onclick="${e(a.onclick)}"` : '';
    html += `<button class="btn btn-xs btn-secondary" id="${e(a.id)}"${onclick}>${e(a.label)}</button>`;
  }
  html += '</div></div>';
  return html;
}

/**
 * Toast shortcut helpers (re-exported from toast.js for convenience).
 * Pages should use window.ShellApi?.Toast instead of importing directly.
 */
export const ToastHelper = {
  success: (msg) => window.ShellApi?.Toast?.success(msg),
  error: (msg) => window.ShellApi?.Toast?.error(msg),
  warning: (msg) => window.ShellApi?.Toast?.warning(msg),
  info: (msg) => window.ShellApi?.Toast?.info(msg),
};
