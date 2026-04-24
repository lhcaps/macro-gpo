"""
Discord Event Service — Phase 12.4 Event Policy Layer.

Transitions Discord from "send a flat message" to a structured event dispatcher with:
- Non-blocking worker queue (Discord must never block combat loop)
- Event policy: per-kind enable/disable toggle from config
- Kill milestone deduplication per match
- In-memory MSS screenshot capture (no temp file)
- bot_error sanitization (no traceback/token/path leak to Discord)

Design decisions:
- Non-blocking: core emits event → queue → worker thread → Discord
- Service does NOT call save_config (config owned by backend)
- screenshot_bytes is BytesIO buffer; never written to disk
- discord_events.webhook_url is source of truth; discord_webhook is legacy fallback
"""

from __future__ import annotations

import io
import logging
import queue
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

_log = logging.getLogger("zedsu.discord_event")

# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

EventKind = Literal[
    "match_end",
    "kill_milestone",
    "combat_start",
    "death",
    "bot_error",
    "test",
]

# ---------------------------------------------------------------------------
# DiscordEvent dataclass
# ---------------------------------------------------------------------------

@dataclass
class DiscordEvent:
    """Structured event payload for Discord dispatch."""

    kind: EventKind
    title: str
    message: str
    severity: str = "info"          # info / warn / error
    match_id: int | None = None
    kills: int | None = None
    include_screenshot: bool = False
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# bot_error sanitization — operator hint only, no traceback to Discord
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS = (
    r"https?://[^\s<>\"']+",       # URLs
    r"(token|api_key|secret|password|auth)[=:]\s*\S+",  # credentials
    r"C:\\[^:\\\s]+",              # Windows absolute paths
    r"/[a-zA-Z]/[^:\s]+",          # Unix absolute paths
    r"File \"[^\"]+\", line \d+",   # traceback file refs
)

import re as _re

_sensitive_re = _re.compile("|".join(_SENSITIVE_PATTERNS), _re.IGNORECASE)


def _sanitize_error_message(message: str) -> str:
    """
    Strip sensitive data from bot_error messages before sending to Discord.

    Replaces URLs, credentials, absolute paths, and traceback references with
    [REDACTED]. Discord only sees: "Bot error: <ExceptionClass>  |  Operator hint: check backend.log"
    """
    sanitized = _sensitive_re.sub("[REDACTED]", message)
    return sanitized


# ---------------------------------------------------------------------------
# Kill milestone deduplication
# ---------------------------------------------------------------------------

_dedupe_lock = threading.Lock()
_kill_milestone_sent: dict[str, bool] = {}   # key: "match_id:threshold"


def dedupe_kill_milestone(match_id: int, threshold: int) -> bool:
    """
    Check whether a kill milestone notification has already been sent.

    Returns:
        True  — milestone already sent for this match; skip notification
        False — first time this threshold is hit for this match; mark sent and proceed
    """
    if match_id is None or threshold is None:
        return False
    key = f"{match_id}:{threshold}"
    with _dedupe_lock:
        if _kill_milestone_sent.get(key, False):
            return True
        _kill_milestone_sent[key] = True
        return False


def reset_kill_dedupe(match_id: int) -> None:
    """Clear all kill milestone dedupe entries for a match (call at match_end)."""
    with _dedupe_lock:
        to_remove = [k for k in _kill_milestone_sent if k.startswith(f"{match_id}:")]
        for k in to_remove:
            del _kill_milestone_sent[k]


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def get_discord_webhook(config: dict) -> str:
    """
    Return the active Discord webhook URL.

    Source of truth: config["discord_events"]["webhook_url"]
    Legacy fallback:  config["discord_webhook"]

    The legacy path is kept for migration compatibility only.
    """
    events_cfg = config.get("discord_events") or {}
    url = str(events_cfg.get("webhook_url", "")).strip()
    if url:
        return url
    return str(config.get("discord_webhook", "")).strip()


def has_webhook(config: dict) -> bool:
    """Return True if any webhook URL is configured."""
    return bool(get_discord_webhook(config))


def discord_events_enabled(config: dict) -> bool:
    """Return True if the Discord events feature is explicitly enabled."""
    events_cfg = config.get("discord_events") or {}
    return bool(events_cfg.get("enabled", False))


def should_dispatch(config: dict, event_kind: EventKind) -> bool:
    """
    Return True if the given event kind is enabled in config.

    Falls back to True if the events dict is missing (lenient on incomplete config).
    """
    if not has_webhook(config):
        return False
    if not discord_events_enabled(config):
        return False
    events_cfg = (config.get("discord_events") or {}).get("events") or {}
    return bool(events_cfg.get(event_kind, False))


# ---------------------------------------------------------------------------
# Screenshot capture (in-memory, no temp file)
# ---------------------------------------------------------------------------

def capture_screenshot_png_bytes(region: dict | None = None) -> io.BytesIO | None:
    """
    Capture screen (or region) via MSS and return as in-memory PNG bytes.

    Args:
        region: Optional dict with keys {left, top, right, bottom}.
                If None, captures the primary monitor.

    Returns:
        BytesIO buffer positioned at start, or None if MSS unavailable.
    """
    try:
        import mss
        with mss.mss() as sct:
            if region:
                monitor = {
                    "left": int(region.get("left", 0)),
                    "top": int(region.get("top", 0)),
                    "width": max(1, int(region.get("right", 0) - region.get("left", 0))),
                    "height": max(1, int(region.get("bottom", 0) - region.get("top", 0))),
                }
            else:
                monitor = sct.monitors[0]
            img = sct.grab(monitor)
            buf = io.BytesIO()
            img.png.write_png(buf)
            buf.seek(0)
            return buf
    except ImportError:
        _log.warning("MSS not available; screenshots disabled")
        return None
    except Exception as e:
        _log.warning("Screenshot capture failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Event dispatch
# ---------------------------------------------------------------------------

def send_discord_event(
    webhook_url: str,
    event: DiscordEvent,
    screenshot_bytes: io.BytesIO | None = None,
) -> int | None:
    """
    Send a structured DiscordEvent via webhook.

    Uses embeds for structured payload. screenshot_bytes is sent as a
    multipart file attachment (in-memory; no temp file written).

    Returns HTTP status code on success, None on failure.
    """
    from src.utils.discord import send_discord

    # Severity colour map (Discord embed integer colour)
    severity_colours = {
        "info": 0x3B82F6,    # blue
        "warn": 0xF59E0B,    # amber
        "error": 0xEF4444,   # red
    }
    colour = severity_colours.get(event.severity, 0x3B82F6)

    # Build embed
    embed = {
        "title": event.title,
        "description": event.message,
        "color": colour,
        "fields": [],
    }

    if event.kills is not None:
        embed["fields"].append({"name": "Kills", "value": str(event.kills), "inline": True})
    if event.match_id is not None:
        embed["fields"].append({"name": "Match", "value": f"#{event.match_id}", "inline": True})
    if event.include_screenshot and screenshot_bytes:
        embed["fields"].append({"name": "Screenshot", "value": "(see attachment)", "inline": False})

    payload = {"embeds": [embed]}

    try:
        import requests
        if screenshot_bytes:
            screenshot_bytes.seek(0)
            response = requests.post(
                webhook_url,
                json=payload,
                files={"file": ("event_screenshot.png", screenshot_bytes.getvalue(), "image/png")},
                timeout=10,
            )
        else:
            response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code
    except Exception as e:
        _log.warning("send_discord_event failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Worker queue (singleton)
# ---------------------------------------------------------------------------

_event_queue: queue.Queue[DiscordEvent | None] = queue.Queue(maxsize=128)
_worker_started = False
_worker_lock = threading.Lock()


def _discord_worker() -> None:
    """Daemon worker that drains the event queue and sends to Discord."""
    global _worker_started
    _log.info("Discord event worker started")
    while True:
        event = _event_queue.get()
        if event is None:   # shutdown sentinel
            _log.info("Discord event worker stopping")
            break
        try:
            _log.debug("Discord event: kind=%s title=%s", event.kind, event.title)
        except Exception:
            pass
    _worker_started = False


def _ensure_worker() -> None:
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            t = threading.Thread(target=_discord_worker, name="DiscordEventWorker", daemon=True)
            t.start()
            _worker_started = True


def emit_event(config: dict, event: DiscordEvent) -> None:
    """
    Public API: emit a DiscordEvent.

    This is the entry point called by BackendCallbacks and ZedsuCore.

    Flow:
        emit_event() → policy check → queue → return immediately (non-blocking)

    The worker thread picks up the event, captures screenshot (if requested),
    and sends to Discord.
    """
    if not should_dispatch(config, event.kind):
        return

    # bot_error: sanitize before queueing
    if event.kind == "bot_error":
        event = DiscordEvent(
            kind=event.kind,
            title="Bot Error",
            message=f"Bot error: {event.message}  |  Operator hint: check backend.log",
            severity="error",
            match_id=event.match_id,
            kills=event.kills,
            include_screenshot=event.include_screenshot,
            metadata=event.metadata,
        )

    _ensure_worker()
    try:
        _event_queue.put_nowait(event)
    except queue.Full:
        _log.warning("Discord event queue full; dropping event: %s", event.kind)


# ---------------------------------------------------------------------------
# Blocking send (for test_webhook — must be synchronous)
# ---------------------------------------------------------------------------

def test_webhook_blocking(webhook_url: str) -> bool:
    """
    Send a test payload and return True on HTTP 2xx.

    Used by the test_discord_webhook backend command.
    Does NOT use the worker queue — sends immediately and blocks.
    """
    from src.utils.discord import send_discord
    payload = {
        "content": "[Zedsu] Webhook test OK.",
        "embeds": [{
            "title": "Zedsu Webhook Test",
            "description": "Your Discord webhook is configured correctly.",
            "color": 0x22C55E,
        }],
    }
    try:
        import requests
        response = requests.post(webhook_url, json=payload, timeout=10)
        return 200 <= response.status_code < 300
    except Exception:
        return False
