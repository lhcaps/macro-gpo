# Phase 13 Wave 3 — Code Review Report

**Reviewer:** gsd-code-reviewer subagent  
**Files reviewed:** 9 files (shell.js, toast.js, confirm.js, diagnostics.js, detection.js, positions.js, hud.js, app.js, index.html)  
**Date:** 2026-04-25

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 2 |
| Warning  | 7 |
| Info     | 5 |
| **Total**| **14** |

---

## Critical Issues (Fixed)

### CR-01: XSS vulnerability in `confirm.js`
**File:** `confirm.js:48`  
**Finding:** `messageEl.innerHTML = String(message)` injected arbitrary HTML/JS into the DOM.  
**Fix Applied:** Changed to `messageEl.textContent = String(message)`.  
**Committed:** `fd380f7`  

### CR-02: ReferenceError in `detection.js`
**File:** `detection.js:145`  
**Finding:** Bare identifier `ShellApi` used in catch block; causes `ReferenceError` before the `window.ShellApi` guard can run.  
**Fix Applied:** Changed `ShellApi` to `window.ShellApi`.  
**Committed:** `fd380f7`  

---

## Warnings

| ID | File | Finding |
|----|------|---------|
| W-01 | shell.js | Silent error swallowing in poll loop — errors caught and swallowed without logging |
| W-02 | diagnostics.js | Event listeners accumulate on page reload |
| W-03 | hud.js | Poll timer memory leak — no cleanup on re-init |
| W-04 | app.js | Variable hoisting — duplicate `var hudOverlay` declarations |
| W-05 | positions.js | Unvalidated JSON import — `JSON.parse` on untrusted input |
| W-06 | confirm.js | Fragile visibility check — relies on `offsetParent` which is fragile for hidden elements |
| W-07 | positions.js | Repeated unnecessary API calls in import flow |

**Recommended:** Address W-03, W-05, and W-07 in a follow-up patch.

---

## Info

- Mixed `var`/`let`/`const` usage across files (consistency issue)
- Unused `async` keywords in `diagnostics.js`
- No cleanup on page navigation
- Hardcoded API base URL
- Inconsistent error handling patterns

---

## Status

- **CR-01** and **CR-02** fixed and committed.
- Warnings and info items are tracked for future cleanup.
