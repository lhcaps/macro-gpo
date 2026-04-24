from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import os
import re
import statistics


LOG_LINE_RE = re.compile(r"^\[(?P<stamp>[^\]]+)\]\s*(?:(?P<error>\[ERROR\])\s*)?(?P<message>.*)$")
MATCH_START_RE = re.compile(r"Match #(?P<match>\d+) started(?: \((?P<reason>[^)]+)\))?\.")

_CACHE = {}


@dataclass
class MatchCycle:
    number: int
    start_time: datetime
    start_reason: str = "standard"
    wait_seconds: int | None = None
    combat_asset_fallbacks: int = 0
    melee_retry_presses: int = 0
    melee_retry_failures: int = 0
    spectating_seconds: int = 0
    post_match_seconds: int = 0
    duration_seconds: int | None = None
    completed: bool = False


class _ParseState:
    def __init__(self):
        self.matches = []
        self.current_match = None
        self.pending_wait_start = None
        self.pending_movement_fallback = False
        self.spectating_start = None
        self.post_match_start = None
        self.time_only_day = date(2000, 1, 1)
        self.last_timestamp = None


def _format_duration(seconds):
    if seconds is None:
        return "n/a"

    seconds = int(max(0, seconds))
    minutes, remainder = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {remainder}s"
    return f"{remainder}s"


def _mean(values):
    if not values:
        return None
    return int(round(statistics.fmean(values)))


def _parse_timestamp(stamp, state):
    stamp = stamp.strip()
    try:
        return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    try:
        parsed_time = datetime.strptime(stamp, "%H:%M:%S").time()
    except ValueError:
        return None

    timestamp = datetime.combine(state.time_only_day, parsed_time)
    if state.last_timestamp and timestamp < state.last_timestamp:
        state.time_only_day += timedelta(days=1)
        timestamp = datetime.combine(state.time_only_day, parsed_time)
    return timestamp


def _finalize_current_match(state, timestamp, completed=False):
    current = state.current_match
    if current is None:
        return

    if state.spectating_start is not None and timestamp is not None:
        current.spectating_seconds += max(0, int((timestamp - state.spectating_start).total_seconds()))
    if state.post_match_start is not None and timestamp is not None and current.post_match_seconds == 0:
        current.post_match_seconds = max(0, int((timestamp - state.post_match_start).total_seconds()))
    if timestamp is not None:
        current.duration_seconds = max(0, int((timestamp - current.start_time).total_seconds()))
    current.completed = completed
    state.matches.append(current)

    state.current_match = None
    state.spectating_start = None
    state.post_match_start = None


def _begin_match(state, match_number, timestamp, reason):
    if state.current_match is not None:
        _finalize_current_match(state, state.last_timestamp, completed=False)

    wait_seconds = None
    if state.pending_wait_start is not None and timestamp is not None:
        wait_seconds = max(0, int((timestamp - state.pending_wait_start).total_seconds()))

    state.current_match = MatchCycle(
        number=match_number,
        start_time=timestamp,
        start_reason=reason or "standard",
        wait_seconds=wait_seconds,
    )
    state.pending_wait_start = None
    state.pending_movement_fallback = False
    state.spectating_start = None
    state.post_match_start = None


def _parse_cycles(log_path):
    state = _ParseState()

    with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue

            match = LOG_LINE_RE.match(line)
            if not match:
                continue

            timestamp = _parse_timestamp(match.group("stamp"), state)
            message = (match.group("message") or "").strip()
            if timestamp is None or not message:
                continue

            state.last_timestamp = timestamp

            start_match = MATCH_START_RE.search(message)
            if start_match:
                reason = start_match.group("reason") or ""
                if not reason and state.pending_movement_fallback:
                    reason = "movement fallback"
                _begin_match(state, int(start_match.group("match")), timestamp, reason)
                continue

            if message == "Waiting for match to fully load.":
                state.pending_wait_start = timestamp
                state.pending_movement_fallback = False
                continue

            if message == "Return to lobby detected in match wait phase. Switching to movement mode.":
                state.pending_movement_fallback = True

            current = state.current_match
            if current is None:
                continue

            if message.startswith("Combat asset was not visible long enough."):
                current.combat_asset_fallbacks += 1
            elif message == "Melee was not confirmed. Pressing slot 1 and checking combat state again.":
                current.melee_retry_presses += 1
            elif message == "Could not confirm melee equip yet. Continuing dynamic movement and retrying.":
                current.melee_retry_failures += 1
            elif message == "Spectating detected during melee loop. Switching to post-death watch.":
                state.spectating_start = timestamp
            elif message == "Results detected while spectating. Switching to post-match handling.":
                if state.spectating_start is not None:
                    current.spectating_seconds += max(0, int((timestamp - state.spectating_start).total_seconds()))
                    state.spectating_start = None
            elif message == "Post-match phase started.":
                state.post_match_start = timestamp
            elif message == "Continue clicked. Returning to lobby.":
                _finalize_current_match(state, timestamp, completed=True)

    if state.current_match is not None:
        _finalize_current_match(state, state.last_timestamp, completed=False)

    return state.matches


def _build_summary(cycles, combat_asset_ready):
    if not cycles:
        return {
            "headline": "Run insights will appear here after the log captures a few queued matches.",
            "summary": "No match cycles were found in the current debug log yet.",
            "recommendations": "- Start the bot, let at least one full queue cycle finish, then check this panel again.",
        }

    recent = cycles[-12:]
    waits = [cycle.wait_seconds for cycle in recent if cycle.wait_seconds is not None]
    movement_fallbacks = sum(1 for cycle in recent if cycle.start_reason == "movement fallback")
    combat_fallbacks = sum(cycle.combat_asset_fallbacks for cycle in recent)
    melee_retry_presses = sum(cycle.melee_retry_presses for cycle in recent)
    melee_retry_failures = sum(cycle.melee_retry_failures for cycle in recent)
    spectating_waits = [cycle.spectating_seconds for cycle in recent if cycle.spectating_seconds > 0]
    post_match_waits = [cycle.post_match_seconds for cycle in recent if cycle.post_match_seconds > 0]
    completed_matches = sum(1 for cycle in recent if cycle.completed)

    summary_parts = [f"{len(recent)} recent match cycle(s)"]
    if waits:
        summary_parts.append(
            f"avg match confirmation {_format_duration(_mean(waits))} (max {_format_duration(max(waits))})"
        )
    if movement_fallbacks:
        summary_parts.append(f"movement fallback {movement_fallbacks}/{len(recent)}")
    if combat_fallbacks or melee_retry_presses or melee_retry_failures:
        summary_parts.append(
            "combat fallback "
            f"{combat_fallbacks} asset miss(es), {melee_retry_presses} slot-1 retry/retries, "
            f"{melee_retry_failures} failed confirmation loop(s)"
        )
    if spectating_waits:
        summary_parts.append(f"spectating watch avg {_format_duration(_mean(spectating_waits))}")
    if post_match_waits:
        summary_parts.append(f"post-match cleanup avg {_format_duration(_mean(post_match_waits))}")
    if completed_matches:
        summary_parts.append(f"{completed_matches}/{len(recent)} completed through result recovery")

    recommendations = []
    avg_wait = _mean(waits)
    max_wait = max(waits) if waits else None

    if avg_wait is not None and (avg_wait >= 180 or (max_wait is not None and max_wait >= 240)):
        recommendations.append(
            "Match confirmation is taking a long time. Re-capture `ultimate` and `return_to_lobby_alone` on the same Roblox client size, and lower confidence slightly if transition detection stalls."
        )

    if movement_fallbacks >= max(1, len(recent) // 4):
        recommendations.append(
            "Movement fallback is showing up often. Keep the Roblox client visible during queue transitions and refresh the queue/start-of-match assets if the HUD has shifted."
        )

    if combat_fallbacks or melee_retry_presses or melee_retry_failures:
        if combat_asset_ready:
            recommendations.append(
                "Combat confirmation is still noisy. Re-capture `combat_ready` from a state where melee is definitely equipped and keep the crop tight around the HUD indicator."
            )
        else:
            recommendations.append(
                "Combat confirmation is relying on slot heuristics. Capture the optional `Combat Equipped Indicator` to stabilize the 5-hit melee loop."
            )

    if spectating_waits and _mean(spectating_waits) >= 600:
        recommendations.append(
            "Results are spending a long time in spectating watch. Re-check the `open`, `continue`, and result-state captures so post-match recovery can exit sooner."
        )

    if not recommendations:
        recommendations.append(
            "No single failure pattern dominated the recent log. Keep captures aligned to the current Roblox client size and refresh them after major UI scale changes."
        )

    headline = "Recent run insights are ready."
    if movement_fallbacks or combat_fallbacks or melee_retry_failures:
        headline = "Recent runs show repeatable weak points worth tightening."
    elif completed_matches >= max(2, len(recent) // 2):
        headline = "Recent runs look mostly stable with consistent result recovery."

    return {
        "headline": headline,
        "summary": " | ".join(summary_parts),
        "recommendations": "\n".join(f"- {item}" for item in recommendations),
    }


def build_runtime_log_insights(log_path, *, combat_asset_ready=False):
    if not log_path:
        return {
            "headline": "Run insights are unavailable.",
            "summary": "No debug log path was provided.",
            "recommendations": "- Point the analyzer at a runtime log file to see recent match patterns.",
        }

    absolute_path = os.path.abspath(log_path)
    if not os.path.exists(absolute_path):
        return {
            "headline": "Run insights are waiting for the first log file.",
            "summary": f"No log file was found at `{absolute_path}` yet.",
            "recommendations": "- Start the app once so it can create the runtime debug log, then revisit this panel.",
        }

    stats = os.stat(absolute_path)
    cache_key = (absolute_path, stats.st_mtime_ns, stats.st_size, bool(combat_asset_ready))
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    cycles = _parse_cycles(absolute_path)
    result = _build_summary(cycles, combat_asset_ready)
    result["source_path"] = absolute_path
    _CACHE.clear()
    _CACHE[cache_key] = result
    return result
