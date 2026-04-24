---
phase: 1
phase_name: "Runtime Run Diagnostics"
project: "Zedsu"
generated: "2026-04-23T00:00:00Z"
counts:
  decisions: 3
  lessons: 3
  patterns: 3
  surprises: 2
missing_artifacts:
  - "01-VERIFICATION.md"
  - "01-UAT.md"
---

# Phase 1 Learnings: Runtime Run Diagnostics

## Decisions

### Keep diagnostics local and EXE-friendly
Runtime insight should come from the existing runtime log instead of new hosted telemetry or external analytics.

**Rationale:** The product already relies on local runtime files and EXE portability.
**Source:** 01-CONTEXT.md

---

### Diagnose the current loop before changing combat behavior again
The first improvement phase should explain repeated weak points instead of rewriting the gameplay loop.

**Rationale:** The long multi-run log shows that recovery usually succeeds; the bigger gap is operator visibility into where instability comes from.
**Source:** 01-CONTEXT.md

---

### Surface recommendations in the dashboard, not only through log parsing utilities
The analyzer had to feed the existing control center directly so non-technical operators benefit without extra tooling.

**Rationale:** The app's value is guided operation, not developer-only debugging.
**Source:** 01-01-SUMMARY.md

---

## Lessons

### Long-run evidence changed the right target
Reading a large historical run log made it clear that the next valuable step was observability, not another blind combat rewrite.

**Context:** The repeated issues were variable match waits, frequent movement fallback, and melee confirmation noise across many completed cycles.
**Source:** C:/Users/ADMIN/Documents/[084000] Waiting for match to fully.txt

---

### The current local debug log can be empty of match cycles even when the product is healthy
The analyzer must degrade cleanly when `debug_log.txt` only contains startup lines or a partial session.

**Context:** Smoke-testing against the repo-local log returned "no match cycles found," which is a valid state and not an analyzer failure.
**Source:** 01-01-SUMMARY.md

---

### Cached parsing matters because the dashboard refreshes frequently
Repeatedly re-reading a large log on every UI refresh would be wasteful, so caching by file metadata is worth doing immediately.

**Context:** `refresh_runtime_summary()` runs on a 1.2-second loop and should stay lightweight.
**Source:** 01-01-SUMMARY.md

---

## Patterns

### Parse runtime behavior as match cycles
Grouping log lines into match-level records makes it much easier to summarize waits, combat retries, spectating, and recovery.

**When to use:** Any time the app emits repeating queue/combat/result phases and the operator cares about session health over individual line noise.
**Source:** 01-01-SUMMARY.md

---

### Turn repeated patterns into setup actions
Diagnostics are most useful when they point directly at captures or settings the operator can refresh.

**When to use:** Desktop automation tools where most instability comes from stale assets, client scale drift, or weak detection anchors.
**Source:** 01-CONTEXT.md

---

### Preserve positive recovery signals alongside failure patterns
The insight layer should highlight that result recovery still works even when transition/combat heuristics are noisy.

**When to use:** Systems with partial instability where a balanced summary is more trustworthy than only red-flag logging.
**Source:** C:/Users/ADMIN/Documents/[084000] Waiting for match to fully.txt

---

## Surprises

### Historical match confirmation times were much longer than expected
The analyzer found recent match confirmation averaging more than five minutes on the provided historical log, with the longest recent wait above eleven minutes.

**Impact:** Match-transition guidance became a required part of the new insight card instead of a minor note.
**Source:** 01-01-SUMMARY.md

---

### Result recovery stayed much more consistent than combat confirmation
Even with frequent combat fallback and long spectating watches, the sampled historical matches still completed through result recovery.

**Impact:** The improvement scope stayed focused on diagnostics and setup guidance rather than a broad runtime rewrite.
**Source:** C:/Users/ADMIN/Documents/[084000] Waiting for match to fully.txt
