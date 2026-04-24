"""
Position Service Layer — Phase 12.1

Typed helpers for managing combat_positions in config.
Service mutates config and returns result; backend owns persistence (save_config).
Fresh window rect on every resolve.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.utils.windows import get_window_rect

_position_log = logging.getLogger("zedsu.position")


def validate_xy(x: Any, y: Any) -> tuple[bool, str | None]:
    """
    Validate x and y as normalized float values in [0.0, 1.0].

    Returns (True, None) on success, (False, error_message) on failure.
    """
    try:
        x_val = float(x)
    except (TypeError, ValueError):
        return False, f"x must be numeric, got {type(x).__name__}"

    if not (0.0 <= x_val <= 1.0):
        return False, f"x={x_val} outside valid range [0.0, 1.0]"

    try:
        y_val = float(y)
    except (TypeError, ValueError):
        return False, f"y must be numeric, got {type(y).__name__}"

    if not (0.0 <= y_val <= 1.0):
        return False, f"y={y_val} outside valid range [0.0, 1.0]"

    return True, None


def validate_position_record(
    name: str, record: Dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Validate a full position record dict.

    Returns (True, None) on success, (False, error_message) on failure.

    Applies defaults for optional fields (label="", enabled=True).
    """
    if not isinstance(name, str):
        return False, f"name must be a string, got {type(name).__name__}"

    if not name.strip():
        return False, "name cannot be empty or whitespace-only"

    if not isinstance(record, dict):
        return False, f"record must be a dict, got {type(record).__name__}"

    if "x" not in record:
        return False, "record must contain 'x' key"

    if "y" not in record:
        return False, "record must contain 'y' key"

    x_valid, x_err = validate_xy(record["x"], record["y"])
    if not x_valid:
        return False, f"record x/y invalid: {x_err}"

    return True, None


def list_positions(config: dict) -> List[Dict[str, Any]]:
    """
    Return all positions from config["combat_positions"] as object records.

    Output keys: name, x, y, label, enabled, captured_at, window_title.
    Returns empty list if no positions.
    """
    positions: Dict[str, Any] = config.get("combat_positions", {})
    if not positions:
        return []

    result: List[Dict[str, Any]] = []
    for name, rec in positions.items():
        result.append({
            "name": name,
            "x": rec.get("x"),
            "y": rec.get("y"),
            "label": rec.get("label", ""),
            "enabled": rec.get("enabled", True),
            "captured_at": rec.get("captured_at", ""),
            "window_title": rec.get("window_title", ""),
        })

    return result


def set_position(
    config: dict,
    name: str,
    x: float,
    y: float,
    label: str | None = None,
    enabled: bool = True,
    captured_at: str | None = None,
    window_title: str | None = None,
) -> tuple[bool, str | None]:
    """
    Store a position in config["combat_positions"].

    Validates x/y before storing.
    Does NOT call save_config() — backend command handler does that.
    Returns (True, None) on success, (False, error_message) on failure.
    """
    xy_valid, xy_err = validate_xy(x, y)
    if not xy_valid:
        return False, xy_err

    norm_x = round(float(x), 6)
    norm_y = round(float(y), 6)

    if "combat_positions" not in config:
        config["combat_positions"] = {}

    config["combat_positions"][name] = {
        "x": norm_x,
        "y": norm_y,
        "label": label or "",
        "enabled": enabled,
        "captured_at": captured_at or "",
        "window_title": window_title or "",
    }

    return True, None


def delete_position(config: dict, name: str) -> tuple[bool, str | None]:
    """
    Delete a position from config["combat_positions"] by name.

    Does NOT call save_config() — backend command handler does that.
    Returns (True, None) on success, (False, error_message) if not found.
    """
    positions = config.get("combat_positions", {})

    if name not in positions:
        return False, f"Position not found: {name}"

    del positions[name]
    return True, None


def resolve_position(config: dict, name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a named position to absolute pixel coordinates.

    Reads game_window_title from config, calls get_window_rect() fresh each time.
    Converts normalized (x, y) to absolute pixel coordinates.

    Returns dict with abs_x/abs_y in pixels, or None if window/position missing.
    """
    title = config.get("game_window_title")
    if not title:
        _position_log.debug("resolve_position: no game_window_title in config")
        return None

    rect = get_window_rect(title)
    if rect is None:
        _position_log.debug("resolve_position: window not found for title=%r", title)
        return None

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top

    positions = config.get("combat_positions", {})
    record = positions.get(name)
    if record is None:
        _position_log.debug("resolve_position: position %r not found in combat_positions", name)
        return None

    norm_x = record["x"]
    norm_y = record["y"]

    abs_x = int(left + norm_x * width)
    abs_y = int(top + norm_y * height)

    return {
        "name": name,
        "abs_x": abs_x,
        "abs_y": abs_y,
        "x": norm_x,
        "y": norm_y,
        "label": record.get("label", ""),
        "enabled": record.get("enabled", True),
    }


def resolve_all_positions(config: dict) -> List[Dict[str, Any]]:
    """
    Resolve all positions in combat_positions to absolute pixel coordinates.

    Gets window rect once (shared across all positions) to avoid redundant calls.
    Returns empty list if window not found.
    """
    title = config.get("game_window_title")
    if not title:
        return []

    rect = get_window_rect(title)
    if rect is None:
        return []

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top

    positions = config.get("combat_positions", {})
    if not positions:
        return []

    result: List[Dict[str, Any]] = []

    for name, record in positions.items():
        norm_x = record["x"]
        norm_y = record["y"]

        abs_x = int(left + norm_x * width)
        abs_y = int(top + norm_y * height)

        result.append({
            "name": name,
            "abs_x": abs_x,
            "abs_y": abs_y,
            "x": norm_x,
            "y": norm_y,
            "label": record.get("label", ""),
            "enabled": record.get("enabled", True),
        })

    return result
