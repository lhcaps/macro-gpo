"""
Match Telemetry — Phase 12.5.

Records per-tick combat timeline as JSONL so the operator can replay what happened
in any match. Designed to never crash the combat loop — telemetry failures are
silent and non-fatal.

Output structure:
  runs/matches/match_XXXX/
    timeline.jsonl     — one JSON line per combat tick
    summary.json      — post-match summary (duration, kills, death_reason, etc.)
    snapshots/        — optional death/crowd screenshots
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CombatTick:
    ts: float                    # Unix timestamp (time.time())
    t_match: float               # Seconds since match start
    match_id: int
    state: str                  # FSM state name: ENGAGED, SCANNING, FLEEING, etc.
    action: str                 # What the bot decided: engage, scan, flee, reposition
    signals: dict               # CombatSignalDetector output
    target: dict                # Target memory state
    risk: dict                  # Situation/risk model output
    decision: dict              # Movement decision


@dataclass
class MatchSummary:
    match_id: int
    started_at: float
    ended_at: float
    duration_sec: float
    kills: int
    death_reason: Optional[str] = None
    exit_state: Optional[str] = None
    total_ticks: int = 0


# ---------------------------------------------------------------------------
# MatchTelemetry — singleton writer
# ---------------------------------------------------------------------------

class MatchTelemetry:
    """
    Thread-safe per-match telemetry writer.

    Usage:
        telemetry = MatchTelemetry(config)
        telemetry.start_match(match_id=7)
        telemetry.record_tick(CombatTick(...))
        telemetry.record_transition("ENGAGED", "FLEEING", "player_hp_low")
        telemetry.finish_match(summary)
    """

    _instance: Optional[MatchTelemetry] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[dict] = None):
        self._config = config or {}
        self._match_dir: Optional[Path] = None
        self._tick_count = 0

    def _timeline_path(self) -> Optional[Path]:
        return self._match_dir / "timeline.jsonl" if self._match_dir else None

    def _summary_path(self) -> Optional[Path]:
        return self._match_dir / "summary.json" if self._match_dir else None

    def _tick_count_path(self) -> Optional[Path]:
        return self._match_dir / "tick_count.txt" if self._match_dir else None

    def _enabled(self) -> bool:
        return self._config.get("combat_ai", {}).get("telemetry_enabled", False)

    # ----- public API -----

    def start_match(self, match_id: int) -> None:
        """Open a new timeline file for this match."""
        if not self._enabled():
            return
        try:
            base = self._config.get("combat_ai", {}).get("telemetry_dir", "runs/matches")
            root = Path(base)
            root.mkdir(parents=True, exist_ok=True)
            match_dir = root / f"match_{match_id:04d}"
            match_dir.mkdir(parents=True, exist_ok=True)
            (match_dir / "snapshots").mkdir(exist_ok=True)
            self._match_dir = match_dir
            self._tick_count = 0
        except Exception:
            self._match_dir = None  # Non-fatal: telemetry disabled on error

    def record_tick(self, tick: CombatTick) -> None:
        """
        Write one combat tick to timeline.jsonl.
        Thread-safe. Raises are caught and suppressed.
        """
        if not self._enabled() or not self._match_dir:
            return
        path = self._timeline_path()
        if not path:
            return
        try:
            sample_rate = self._config.get("combat_ai", {}).get("telemetry_sample_rate", 1.0)
            if sample_rate < 1.0 and __import__("random").random() > sample_rate:
                return
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(tick), ensure_ascii=False) + "\n")
            self._tick_count += 1
            cp = self._tick_count_path()
            if cp:
                with open(cp, "w") as f:
                    f.write(str(self._tick_count))
        except Exception:
            pass  # Never crash combat loop for telemetry failures

    def record_transition(self, old_state: str, new_state: str, reason: str) -> None:
        """Log a state transition as a special tick."""
        if not self._enabled() or not self._match_dir:
            return
        self.record_tick(CombatTick(
            ts=time.time(),
            t_match=0.0,
            match_id=0,
            state=f"{old_state}→{new_state}",
            action="transition",
            signals={"_reason": reason},
            target={},
            risk={},
            decision={"reason": reason},
        ))

    def record_event(self, kind: str, payload: dict) -> None:
        """Log a discrete combat event (death, kill, etc.) as a tick."""
        if not self._enabled() or not self._match_dir:
            return
        self.record_tick(CombatTick(
            ts=time.time(),
            t_match=0.0,
            match_id=0,
            state="EVENT",
            action=kind,
            signals=payload,
            target={},
            risk={},
            decision=payload,
        ))

    def finish_match(self, summary: MatchSummary) -> None:
        """Write summary.json after a match ends."""
        if not self._enabled() or not self._match_dir:
            return
        path = self._summary_path()
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(summary), f, indent=2)
        except Exception:
            pass

    def snapshot(self, name: str, image_bytes: bytes) -> None:
        """
        Save a PNG snapshot (e.g., death screenshot) to snapshots/.
        Called when snapshot_on_death=True.
        """
        if not self._enabled() or not self._match_dir:
            return
        try:
            snap_dir = self._match_dir / "snapshots"
            snap_dir.mkdir(exist_ok=True)
            path = snap_dir / f"{name}_{int(time.time() * 1000)}.png"
            with open(path, "wb") as f:
                f.write(image_bytes)
        except Exception:
            pass

    def get_last_ticks(self, n: int = 10) -> list[dict]:
        """
        Read the last N ticks from timeline.jsonl.
        Used by DeathClassifier to reconstruct pre-death context.
        """
        path = self._timeline_path()
        if not path or not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            ticks = [json.loads(l) for l in lines[-n:] if l.strip()]
            return ticks
        except Exception:
            return []

    # ----- singleton -----

    @classmethod
    def get_instance(cls, config: Optional[dict] = None) -> "MatchTelemetry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """For testing only."""
        with cls._lock:
            cls._instance = None
