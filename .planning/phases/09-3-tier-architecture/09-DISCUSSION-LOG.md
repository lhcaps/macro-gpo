# Phase 9: 3-Tier Architecture Revamp - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 09-3-tier-architecture
**Areas discussed:** 9a (Callback Pattern), 9b (State Format), 9c (Backend Port & Auth), 9d (HUD/Overlay Design), 9e (Hotkey Management), 9f (Migration Strategy), 9g (IPC Scope)

---

## 9a: ZedsuCore Callback Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Interface-based callbacks | Protocol + TypedDict — clean, typed, testable | ✓ |
| Simple function dict | `{"on_log": fn, "on_status": fn}` | |
| Event emitter | ZedsuCore emits events, Backend subscribes | |

**User's choice:** Interface-based callbacks (Protocol + TypedDict)
**Notes:** Typed interfaces give better IDE support, type checking, and testability.

---

## 9b: State Snapshot Format

| Option | Description | Selected |
|--------|-------------|----------|
| Flat JSON snapshot | Simple, all fields in one dict | |
| Hierarchical JSON | Nested sections (combat, vision, config, stats) | ✓ |
| Delta updates | Full state on change, incremental otherwise | |

**User's choice:** Hierarchical JSON
**Notes:** Cleaner to work with in frontend JS, groups related data naturally.

---

## 9c: Backend Port & Auth

### Port

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed port (9761 or 8080) | Simple, consistent | ✓ |
| Dynamic port | Find empty port, save to temp file | |
| Environment variable | PORT=9761, fallback dynamic | |

**User's choice:** Fixed port 9761
**Notes:** Adjacent to Bridger's 9760, easy to remember and associate.

### Authentication

| Option | Description | Selected |
|--------|-------------|----------|
| No auth | localhost only, no need | ✓ |
| Simple token | Header X-Zedsu-Token: <uuid> | |

**User's choice:** No authentication
**Notes:** Localhost-only deployment, no external exposure.

---

## 9d: Frontend Overlay / HUD Design

**User feedback (detailed):**

User wants a premium HUD with sci-fi/tech aesthetic. Key elements:

1. **Glassmorphism** — Semi-transparent background with blur: `background: rgba(10, 10, 10, 0.5); backdrop-filter: blur(8px)`. No solid black background.

2. **Neon Glow & Status Colors** — Use box-shadow and text-shadow for glow effect. Color changes by state:
   - IDLE → White/Gray
   - SCANNING → Blue (subtle pulse animation)
   - COMBAT/ENGAGED → Red (intense glow)
   - SPECTATING → Yellow/Orange
   - POST_MATCH → Green
   - Error/Crash → Red blinking

3. **Typography** — Monospace font (JetBrains Mono, Roboto Mono, or Orbitron) for numbers/stats. Prevents jitter on value changes.

4. **Smooth Transitions** — CSS transitions when state changes. Color fade + subtle shake animation during combat state. No jarring flashes.

5. **Tauri Config:** `transparent: true, decorations: false, alwaysOnTop: true, skipTaskbar: true`

**User's choice:** Minimal overlay with premium HUD design
**Notes:** User wants it "nhỏ nhưng có võ" — small but with substance. Sci-fi aesthetic with glassmorphism, neon glow, monospace, smooth transitions.

---

## 9e: Hotkey Management

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend (Rust) | Tauri's global shortcut API, recommended | ✓ |
| Backend (Python keyboard module) | Like Bridger | |
| Both | Rust for F1-F5, Python for F6-F12 | |

**User's choice:** Frontend (Rust) handles hotkeys
**Notes:** Using Tauri's native global shortcut API keeps logic in Rust layer, cleaner architecture.

---

## 9f: Migration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Big bang | Rewrite all 3 tiers at once, then integrate | |
| Bottom-up | Tier 1 → Tier 2 → Tier 3 (inside out) | ✓ |
| Top-down | Tier 3 shell first, then fill in logic | |

**User's choice:** Bottom-up
**Notes:** Start from innermost layer (ZedsuCore). Test each tier independently before adding the next. Safest approach for a large refactor.

---

## 9g: Frontend IPC Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal 3 commands | send_action, get_state, restart_backend | ✓ |
| Bridger parity | 9 commands like Bridger | |

**User's choice:** Minimal 3 commands
**Notes:** Simpler is better. Only what's needed: send action to backend, poll state, restart on crash.

---

## the agent's Discretion

- Specific monospace font choice — deferred to Phase 10 implementation
- Overlay exact dimensions — deferred to Phase 10 UI design
- Hotkey default bindings — deferred to Phase 10
- ZedsuCore threading model — deferred to planner
- ZedsuCore entry point API (start/stop/pause) — deferred to planner
- Overlay animation specifics (pulse timing, shake intensity) — deferred to Phase 10

## Deferred Ideas

- Multi-monitor support → Phase 10
- Auto-update mechanism → Phase 14
- Mobile companion app → Out of scope
- YOLO training automation → Phase 11
- Audio detection (FFT) → Not applicable to GPO BR bot

## Scope Creep Redirected

None — discussion stayed within phase scope.
