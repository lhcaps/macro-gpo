# Phase 1 Plan 01 Summary: Runtime Run Diagnostics

## Outcome

Implemented a new cached runtime-log analyzer and surfaced its output inside the dashboard as a dedicated "Recent Run Insights" card. The control center can now summarize repeated match-cycle behavior from `debug_log.txt` without asking the operator to manually read raw log lines.

## What Changed

- Added `src/utils/run_analysis.py` to parse compatible runtime logs, cache results by file metadata, and summarize:
  - match confirmation timing
  - movement fallback frequency
  - combat asset fallback counts
  - slot-1 melee retry pressure
  - spectating and post-match recovery duration
- Integrated the analyzer into `src/ui/app.py` so `refresh_runtime_summary()` updates a new dashboard card with:
  - a short health headline
  - a compact metrics summary
  - concrete setup/capture recommendations
- Added an `Open Debug Log` shortcut to the dashboard runtime controls.
- Updated `README.md` so the new diagnostics capability is visible in the product summary.

## Verification

- `python -m compileall src main.py`
  - Passed.
- `python -c "from pprint import pprint; from src.utils.run_analysis import build_runtime_log_insights; pprint(build_runtime_log_insights('debug_log.txt', combat_asset_ready=False))"`
  - Passed. Current local `debug_log.txt` has startup lines only, so the analyzer correctly reports that more match cycles are needed before insights appear.
- `python -c "from pprint import pprint; from src.utils.run_analysis import build_runtime_log_insights; pprint(build_runtime_log_insights(r'C:\\Users\\ADMIN\\Documents\\[084000] Waiting for match to fully.txt', combat_asset_ready=False))"`
  - Passed. The analyzer surfaced the expected repeated patterns from the long historical log, including long confirmation times, frequent movement fallback, heavy combat heuristics, and long spectating watch.

## Notes

- I did not launch the full Tkinter UI interactively in this turn, so the verification is import/compile plus analyzer smoke tests rather than a manual click-through.
- The analyzer already accepts arbitrary compatible log files at the utility level, but the dashboard currently reads the runtime `debug_log.txt` only.

---

*Completed: 2026-04-23*
