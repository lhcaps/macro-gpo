# Phase 1: Runtime Run Diagnostics - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds runtime intelligence to the existing control center so repeated queue/combat/recovery patterns from the debug log are summarized inside the app. It does not change the gameplay strategy itself; it explains where the current loop is weak or unstable.

</domain>

<decisions>
## Implementation Decisions

### Evidence source
- **D-01:** Use the runtime `debug_log.txt` as the primary source for diagnostics because it already exists in both source and EXE runs.
- **D-02:** The parser should also accept compatible historical logs with either short timestamps or full timestamps so the analyzer logic is reusable beyond one file format.

### Insight scope
- **D-03:** Focus on the patterns that repeated in the long multi-run log: match wait duration, movement fallback during match transition, combat-asset fallback frequency, melee retry pressure, and spectating/result recovery time.
- **D-04:** Summarize recent matches, not full project history, so the dashboard stays responsive and operator-focused.

### Operator guidance
- **D-05:** Convert repeated patterns into short recommendations tied to current setup actions, especially re-capturing `ultimate`, `return_to_lobby`, `open`, `continue`, or `combat_ready`.
- **D-06:** Keep guidance local and lightweight; do not add hosted telemetry or external analytics.

### the agent's Discretion
- Exact thresholds for "long wait" and "repeated fallback"
- Exact wording/layout of the dashboard insight card
- Whether to highlight positive stability notes when the recent log looks healthy

</decisions>

<specifics>
## Specific Ideas

- The user explicitly framed this task around "many runs", so the app should act like a smart operator assistant that learns from repeated cycles instead of just printing more raw log lines.
- The long log shows real evidence that post-match recovery often succeeds even when match transition and melee confirmation stay noisy; the diagnostics should preserve that nuance.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and runtime flow
- `README.md` - Current product framing, guided setup flow, combat loop description, and packaging behavior
- `src/ui/app.py` - Dashboard structure, runtime summary loop, setup gating, and live-log UI
- `src/core/bot_engine.py` - Match wait, movement fallback, combat loop, spectating watch, and post-match transitions
- `src/utils/config.py` - Runtime paths, setup issues, optional warnings, and portability checks

### Run evidence
- `C:/Users/ADMIN/Documents/[084000] Waiting for match to fully.txt` - Multi-run evidence showing repeated wait, movement fallback, melee fallback, and spectating patterns that should drive the diagnostics

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ui/app.py::refresh_runtime_summary` already assembles setup and portability feedback on a 1.2s loop, making it the right integration point for lightweight run insights.
- `LOG_FILE` from `src/utils/config.py` already abstracts source-vs-EXE runtime path handling.

### Established Patterns
- The app favors plain-language guidance over developer-only diagnostics.
- Runtime warnings are already surfaced in dashboard labels and message boxes, so the new insight surface should match that style.

### Integration Points
- Add a new utility module for cached log analysis.
- Call that analyzer from `refresh_runtime_summary`.
- Render the resulting summary and recommendations in a dedicated dashboard card above the live log.

</code_context>

<deferred>
## Deferred Ideas

- Manual import/picker for alternate log files inside the UI - valuable, but not required to get the first insight surface shipped
- Structured per-match JSON/CSV telemetry - useful later if raw log analysis becomes limiting
- Combat strategy rewrites - explicitly outside this phase

</deferred>

---

*Phase: 01-runtime-run-diagnostics*
*Context gathered: 2026-04-23*
