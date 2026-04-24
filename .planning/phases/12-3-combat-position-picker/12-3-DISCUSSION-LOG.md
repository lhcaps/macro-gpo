# Phase 12.3: Combat Position Picker - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 12.3-combat-position-picker
**Areas discussed:** Click lifecycle, Position naming source

---

## Click Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Single-shot (recommended) | Overlay closes immediately after one click. Operator triggers pick_position again for each position. Simpler, no ambiguity. | ✓ |
| Multi-capture with done button | Overlay stays open until explicit close (Esc). Operator clicks multiple positions in one session. Faster for bulk setup, but needs tracking logic for which position is next. | |

**User's choice:** Single-shot
**Notes:** Single-shot is recommended. Multi-capture adds complexity with position ordering state.

---

## Position Naming Source

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend sends name in payload (recommended) | Operator picks position name from Tauri UI dropdown/button first, then triggers pick_position with the name in payload. Clean separation. | ✓ |
| Inline selection in overlay | Overlay shows a list to pick from after clicking. Everything happens inside the overlay. | |
| Auto-assign from defaults | Picks next unused default name automatically. Least flexible. | |

**User's choice:** Frontend sends name in payload
**Notes:** Clean separation. Frontend owns naming, backend owns capture.

---

## Deferred Ideas

None surfaced during this discussion.

---
