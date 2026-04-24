# Phase 2: Radical UI Simplification - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase rebuilds the UI to be radically minimal: the app opens and runs without requiring any setup interaction if config already exists. Settings are accessible but non-blocking. The complex dashboard, insights panel, and readiness checklist are removed or collapsed. Core philosophy: "Get shit done."

</domain>

<decisions>
## Implementation Decisions

### Core philosophy
- **D-01:** Minimal UI - open and run. If config is set, user clicks START and goes.
- **D-02:** Settings accessible but non-blocking - user can ignore if already configured.
- **D-03:** No complex dashboard - simple single view with essential controls.
- **D-04:** Scalable for small screens and high-DPI displays.

### UI Structure
- **D-05:** Single main view with START/STOP button and essential status.
- **D-06:** Settings in a collapsible panel or secondary tab (not blocking).
- **D-07:** Runtime status visible at a glance (minimal, not verbose).
- **D-08:** Remove or collapse the insights panel and readiness checklist.
- **D-09:** Responsive scaling - proper font sizes, layout adapts to window size.

### Technical
- **D-10:** Preserve all existing functionality: asset capture, coordinate picking, bot loop.
- **D-11:** Cross-machine portability: DPI scaling, window binding, config migration.
- **D-12:** Detection performance optimization: smarter caching, faster bot loop.

### Agent's Discretion
- Exact layout of the minimal main view
- How settings are collapsed/shown
- How to handle first-run vs subsequent runs
- Color scheme (current or simplified)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core source files
- `src/ui/app.py` - Current dashboard UI, refresh loop, all tabs
- `src/ui/components.py` - CoordinatePicker, AreaPicker
- `src/core/bot_engine.py` - Bot loop, state machine
- `src/utils/config.py` - Config loading, path resolution
- `src/core/vision.py` - Detection, caching
- `src/utils/run_analysis.py` - Diagnostics (to be optionally shown or removed)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ZedsuApp` class structure - can be simplified
- `refresh_runtime_summary` loop - can be replaced with simpler status
- Theme styling (clam theme, accent colors) - keep consistent
- `_apply_responsive_layout` - existing but insufficient for small screens

### Established Patterns
- Tkinter + ttk for UI (no alternatives - must stay)
- Tab-based navigation (notebook) - can be simplified
- Card-based layout in dashboard - can be removed or minimized
- Console log panel - can be reduced or removed for minimal view

### Integration Points
- `ZedsuApp.__init__` - entry point, theme setup
- `_build_dashboard_tab` - current complex dashboard
- `_build_setup_tab` - settings (move to collapsible)
- `_build_assets_tab` - asset capture (can be secondary)
- `_build_controls_tab` - utilities (can be secondary)
- `refresh_runtime_summary` - 1.2s loop (can be simplified)

</code_context>

<deferred>
## Deferred Ideas

- Full insights panel redesign - removed from Phase 2 scope
- Readiness checklist redesign - removed from Phase 2 scope
- Complex multi-panel dashboard - removed from Phase 2 scope
- Full UI rewrite - incremental simplification only

</deferred>

---

*Phase: 02-radical-ui-simplification*
*Context gathered: 2026-04-24*
