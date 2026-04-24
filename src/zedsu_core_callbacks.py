"""
ZedsuCore Callbacks — typed interface between ZedsuCore and ZedsuBackend.

This module defines the Protocol + TypedDict contract (per D-09a).
All other tiers depend on it.
"""
from typing import Protocol, TypedDict, Optional, Callable, Any


# ============================================================================
# TypedDict Payloads
# ============================================================================


class LogPayload(TypedDict):
    msg: str
    level: str  # "info" | "warn" | "error"


class StatusPayload(TypedDict):
    text: str
    color: str  # hex color like "#16a34a"


class DiscordPayload(TypedDict):
    message: str
    screenshot_path: Optional[str]
    event: str  # "match_end", "timeout", "info"


# ============================================================================
# CoreCallbacks Protocol
# ============================================================================


class CoreCallbacks(Protocol):
    """
    Interface for ZedsuCore → ZedsuBackend communication.
    ZedsuCore calls these; ZedsuBackend implements them.

    Per D-09a: Protocol + TypedDict, clean and typed.
    """

    def log(self, msg: str, level: str = "info") -> None:
        """Log a message. Backend writes to file + forwards to frontend."""
        ...

    def status(self, text: str, color: str = "#475569") -> None:
        """Update status display. Backend broadcasts to frontend via /state."""
        ...

    def discord(self, message: str, screenshot_path: Optional[str] = None, event: str = "info") -> None:
        """Send Discord notification. Backend calls send_discord()."""
        ...

    def config(self) -> dict:
        """Return current config dict. Called every time the bot reads config."""
        ...


    def is_running(self) -> bool:
        """Check if the bot should continue running. Return False to signal stop."""
        ...


    def sleep(self, seconds: float) -> bool:
        """
        Sleep with stop-check. Return True if slept full duration, False if interrupted.
        ZedsuCore uses this instead of time.sleep().
        """
        ...


    def log_error(self, msg: str) -> None:
        """Log an error message. Convenience method."""
        ...


    def invalidate_runtime_caches(self, clear_region: bool = False) -> None:
        """Invalidate runtime caches. Called on window focus change."""
        ...


    def get_search_region(self) -> Optional[dict]:
        """Return the current window region dict or None if no window."""
        ...

    def is_visible(self, image_key: str, confidence: Optional[float] = None, search_context: Optional[dict] = None) -> bool:
        """Check if an asset image is visible in the search region."""
        ...

    def safe_find_and_click(self, image_key: str, confidence: Optional[float] = None) -> bool:
        """Find and click an asset, returning True if found and clicked."""
        ...


    def build_search_context(self) -> dict:
        """Build the current search context (window rect + screenshot)."""
        ...


    def resolve_coordinate(self, key: str) -> Optional[tuple]:
        """Resolve a coordinate key to absolute (x, y) or None."""
        ...

    def resolve_outcome_area(self) -> Optional[tuple]:
        """Resolve the outcome area (left, top, right, bottom) or None."""
        ...


    def locate_image(self, image_key: str, confidence: Optional[float] = None) -> Optional[tuple]:
        """Locate an image and return (left, top, width, height) or None."""
        ...

    def click_saved_coordinate(self, key: str, label: str, clicks: int = 1) -> bool:
        """Click a saved coordinate by key."""
        ...


    def get_combat_detector(self):
        """Get or create the combat signal detector."""
        ...

    def get_yolo_detector(self):
        """Get or create the YOLO detector."""
        ...

    def get_combat_state(self) -> str:
        """Return current combat state name."""
        ...

    def get_combat_debug_info(self) -> dict:
        """Return combat debug info."""
        ...

    def reset_combat(self) -> None:
        """Reset the combat detector."""
        ...

    def on_match_detected(self, reason: str = "") -> None:
        """Called when a match is detected. Records match count."""
        ...

    def invalidate_region_cache(self) -> None:
        """Invalidate the cached search region."""
        ...


# ============================================================================
# No-Op fallback implementation
# ============================================================================


class NoOpCallbacks:
    """
    Default callbacks that do nothing.
    Use when ZedsuCore runs standalone without a backend.
    """

    def log(self, msg, level="info"):
        pass

    def status(self, text, color="#475569"):
        pass

    def discord(self, message, screenshot_path=None, event="info"):
        pass

    def config(self):
        return {}

    def is_running(self):
        return False

    def sleep(self, seconds):
        import time
        time.sleep(seconds)
        return True

    def log_error(self, msg):
        pass

    def invalidate_runtime_caches(self, clear_region=False):
        pass

    def get_search_region(self):
        return None

    def is_visible(self, image_key, confidence=None, search_context=None):
        return False

    def safe_find_and_click(self, image_key, confidence=None):
        return False

    def build_search_context(self):
        return {}

    def resolve_coordinate(self, key):
        return None

    def resolve_outcome_area(self):
        return None

    def locate_image(self, image_key, confidence=None):
        return None

    def click_saved_coordinate(self, key, label, clicks=1):
        return False

    def get_combat_detector(self):
        return None

    def get_yolo_detector(self):
        return None

    def get_combat_state(self):
        return "IDLE"

    def get_combat_debug_info(self):
        return {}

    def reset_combat(self):
        pass

    def on_match_detected(self, reason=""):
        pass

    def invalidate_region_cache(self):
        pass


# ============================================================================
# Factory
# ============================================================================


def create_callbacks(callbacks: Optional[CoreCallbacks] = None) -> CoreCallbacks:
    """Create callbacks instance, using NoOpCallbacks if None provided."""
    return callbacks or NoOpCallbacks()
