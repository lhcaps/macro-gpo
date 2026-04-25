// page-lifecycle.js — Page lifecycle management for Zedsu shell router
// Each page module calls registerPage() when loaded, unregisterPage() when leaving.
// Shell.js calls cleanupCurrentPage() before switching pages.

import { clearCache } from './dom.js';

/**
 * @type {Map<string, {cleanup: Function|null, container: Element|null}>}
 */
const _activePages = new Map();

/**
 * Register a page as active. Call from page module's load() function.
 * @param {string} pageName
 * @param {Element} container - The DOM container for this page
 * @param {Function|null} cleanup - Optional cleanup function to call on leave
 */
export function registerPage(pageName, container, cleanup) {
  // If a page with this name is already registered, clean it up first
  if (_activePages.has(pageName)) {
    const existing = _activePages.get(pageName);
    if (existing.cleanup && typeof existing.cleanup === 'function') {
      try {
        existing.cleanup();
      } catch (err) {
        console.warn(`[PageLifecycle] cleanup error for "${pageName}":`, err);
      }
    }
  }
  _activePages.set(pageName, { cleanup: cleanup || null, container });
}

/**
 * Unregister a page. Call cleanup and remove from registry.
 * @param {string} pageName
 */
export function unregisterPage(pageName) {
  if (!_activePages.has(pageName)) return;
  const { cleanup } = _activePages.get(pageName);
  _activePages.delete(pageName);
  if (cleanup && typeof cleanup === 'function') {
    try {
      cleanup();
    } catch (err) {
      console.warn(`[PageLifecycle] cleanup error for "${pageName}":`, err);
    }
  }
  // Clear DOM query cache so stale refs are refreshed on next visit
  clearCache();
}

/**
 * Get the cleanup function for a specific page without unregistering.
 * @param {string} pageName
 * @returns {Function|null}
 */
export function getPageCleanup(pageName) {
  return _activePages.get(pageName)?.cleanup || null;
}

/**
 * Check if a page is currently registered.
 * @param {string} pageName
 * @returns {boolean}
 */
export function isPageActive(pageName) {
  return _activePages.has(pageName);
}
