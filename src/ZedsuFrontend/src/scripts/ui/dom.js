// dom.js — DOM helper utilities for Zedsu frontend
// Provides cached querySelector and safe event binding.
// Prevents repeated DOM queries and memory leaks from forgotten removeEventListener.

const _cache = new Map();

/**
 * Cached querySelector. Same as document.querySelector but memoizes by selector+parent.
 * Only works for IDs (uses getElementById) or unique selectors.
 * @param {string} selector
 * @param {Element|Document} [root=document]
 * @returns {Element|null}
 */
export function $(selector, root = document) {
  const key = selector + (root === document ? '' : '::' + (root.id || '?'));
  if (!_cache.has(key)) {
    _cache.set(key, root.querySelector(selector));
  }
  return _cache.get(key);
}

/**
 * Clear the query cache. Call this on page navigation to avoid stale refs.
 * @param {string} [selector] - If provided, clears only that key. Otherwise clears all.
 */
export function clearCache(selector) {
  if (selector) {
    _cache.delete(selector);
  } else {
    _cache.clear();
  }
}

/**
 * Safe event binding — automatically removes old handler if re-bound.
 * Useful for poll/callback patterns where the same handler is registered multiple times.
 * @param {Element|Window|Document} target
 * @param {string} event
 * @param {string} handlerKey - Unique key for this handler (for dedup)
 * @param {Function} handler
 */
const _handlers = new Map();

export function on(target, event, handlerKey, handler) {
  if (_handlers.has(handlerKey)) {
    const prev = _handlers.get(handlerKey);
    target.removeEventListener(event, prev);
  }
  target.addEventListener(event, handler);
  _handlers.set(handlerKey, handler);
}

/**
 * Remove a registered handler by key.
 * @param {Element|Window|Document} target
 * @param {string} event
 * @param {string} handlerKey
 */
export function off(target, event, handlerKey) {
  const handler = _handlers.get(handlerKey);
  if (handler) {
    target.removeEventListener(event, handler);
    _handlers.delete(handlerKey);
  }
}

/**
 * Create a cleanup function for a registered handler.
 * Returns a function that, when called, removes the handler.
 * @param {Element|Window|Document} target
 * @param {string} event
 * @param {string} handlerKey
 * @returns {Function}
 */
export function cleanupHandler(target, event, handlerKey) {
  return () => off(target, event, handlerKey);
}

/**
 * Batch textContent update — only updates if value changed.
 * Avoids unnecessary reflows when poll loop sets the same value repeatedly.
 * @param {Element|null} el
 * @param {string|number} value
 */
export function updateText(el, value) {
  if (!el) return;
  const str = String(value ?? '');
  if (el.textContent !== str) {
    el.textContent = str;
  }
}

/**
 * Batch className update — only changes if different.
 * @param {Element|null} el
 * @param {string} className
 */
export function updateClass(el, className) {
  if (!el) return;
  if (el.className !== className) {
    el.className = className;
  }
}
