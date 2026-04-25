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
| W-03 | hud.js | Poll timer memory leak — no cleanup on re-init | **FIXED** `39fc606`: `clearInterval` before `setInterval` in `initHud` |
| W-04 | app.js | Variable hoisting — duplicate `var hudOverlay` declarations | — |
| W-05 | positions.js | Unvalidated JSON import — `JSON.parse` on untrusted input | **FIXED** `39fc606`: schema validation, type checks, per-failure error messages |
| W-06 | confirm.js | Fragile visibility check — relies on `offsetParent` which is fragile for hidden elements | — |
| W-07 | positions.js | Repeated unnecessary API calls in import flow | **FIXED** `39fc606`: batched via `Promise.all`, reports exact saved count |

**Recommended:** W-01, W-02, W-04, W-06 are non-blocking informational items.

---

## Status

- **CR-01** and **CR-02** fixed and committed (`fd380f7`).
- **W-03**, **W-05**, **W-07** fixed and committed (`39fc606`).
- W-01, W-02, W-04, W-06 are non-blocking informational items.
