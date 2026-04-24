# Phase 12.5.1: AI Runtime Wiring Hardening — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 12.5.1-AI Runtime Wiring Hardening
**Areas discussed:** 7 bugs identified from post-12.5 execution review

---

## Bug Fix Scope

All 7 bugs came from post-Phase 12.5 execution review. No gray areas required discussion — all were correctness issues with a single obvious fix.

| # | Area | Bug | Selected Fix |
|---|------|-----|-------------|
| 1 | Harness compile | subprocess returncode not checked | Check returncode == 0, append FAIL on non-zero |
| 2 | Target memory | update() called twice per tick | Single update, keep object, reuse for situation model |
| 3 | YOLO feed | Only SCANNING, not ENGAGED | Extend to SCANNING+APPROACH+ENGAGED, throttle 0.5-0.8s |
| 4 | Crowd risk | visible_enemy_count capped at 0/1 | Feed raw YOLO count, decay fallback |
| 5 | Movement policy | reposition/flee can't preempt M1 | Check intent BEFORE M1 burst |
| 6 | Camera correction | getattr on dict always returns 0.0 | Pass object not dict |
| 7 | Death classifier | combat_death before zone_death | Reorder: zone before combat |

## Deferred Ideas

None — all items are within Phase 12.5.1 scope.
