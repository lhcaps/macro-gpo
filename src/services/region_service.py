"""
Region Service Layer — Phase 12.1

Typed helpers for managing combat_regions_v2 in config.
Service mutates config and returns result; backend owns persistence (save_config).
Fresh window rect on every resolve.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.utils.windows import get_window_rect

_region_log = logging.getLogger("zedsu.region")


def validate_area(area: List[float]) -> tuple[bool, str | None]:
    """
    Validate a normalized [x1, y1, x2, y2] area list.

    Returns (True, None) on success, (False, error_message) on failure.
    """
    if not isinstance(area, (list, tuple)):
        return False, f"area must be list or tuple, got {type(area).__name__}"

    if len(area) != 4:
        return False, f"area must have exactly 4 values [x1,y1,x2,y2], got {len(area)}"

    x1, y1, x2, y2 = area

    for i, (label, val) in enumerate([("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)]):
        if not isinstance(val, (int, float)):
            return False, f"area[{i}] ({label}) must be numeric, got {type(val).__name__}"
        if not (0.0 <= val <= 1.0):
            return False, f"area[{i}] ({label})={val} outside valid range [0.0, 1.0]"

    if x1 >= x2:
        return False, f"x1 ({x1}) must be less than x2 ({x2})"
    if y1 >= y2:
        return False, f"y1 ({y1}) must be less than y2 ({y2})"

    if (x2 - x1) * (y2 - y1) <= 0:
        return False, f"region area must be positive, got zero-area bbox {[x1, y1, x2, y2]}"

    return True, None


def validate_region_record(
    name: str, record: Dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Validate a full region record dict.

    Returns (True, None) on success, (False, error_message) on failure.

    Applies defaults for optional fields (kind="generic", enabled=True).
    """
    if not isinstance(name, str):
        return False, f"name must be a string, got {type(name).__name__}"

    if not name.strip():
        return False, "name cannot be empty or whitespace-only"

    if not isinstance(record, dict):
        return False, f"record must be a dict, got {type(record).__name__}"

    if "area" not in record:
        return False, "record must contain 'area' key"

    area_valid, area_err = validate_area(record["area"])
    if not area_valid:
        return False, f"record['area'] is invalid: {area_err}"

    kind = record.get("kind", "generic")
    if not isinstance(kind, str) or not kind:
        return False, f"record['kind'] must be a non-empty string, got {type(kind).__name__}"

    threshold = record.get("threshold")
    if threshold is not None:
        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            return False, f"record['threshold'] must be numeric, got {type(threshold).__name__}"
        if threshold < 0:
            return False, f"record['threshold'] must be >= 0, got {threshold}"

    enabled = record.get("enabled", True)
    if not isinstance(enabled, bool):
        return False, f"record['enabled'] must be a bool, got {type(enabled).__name__}"

    return True, None


def list_regions(config: dict) -> List[Dict[str, Any]]:
    """
    Return all regions from config["combat_regions_v2"] as object records.

    Output keys: name, area, enabled, kind, threshold, label.
    Does NOT include migrated_from (internal metadata).
    Returns empty list if no regions.
    """
    regions: Dict[str, Any] = config.get("combat_regions_v2", {})
    if not regions:
        return []

    result: List[Dict[str, Any]] = []
    for name, rec in regions.items():
        result.append({
            "name": name,
            "area": rec.get("area"),
            "enabled": rec.get("enabled", True),
            "kind": rec.get("kind", "generic"),
            "threshold": rec.get("threshold"),
            "label": rec.get("label", ""),
        })

    return result


def set_region(
    config: dict,
    name: str,
    area: List[float],
    kind: str = "generic",
    threshold: float | None = None,
    enabled: bool = True,
    label: str | None = None,
) -> tuple[bool, str | None]:
    """
    Store a region in config["combat_regions_v2"].

    Validates area and record before storing.
    Does NOT call save_config() — backend command handler does that.
    Returns (True, None) on success, (False, error_message) on failure.
    """
    area_valid, area_err = validate_area(area)
    if not area_valid:
        return False, f"invalid area: {area_err}"

    record_valid, record_err = validate_region_record(
        name, {"area": area, "kind": kind, "threshold": threshold, "enabled": enabled}
    )
    if not record_valid:
        return False, record_err

    name = name.strip()

    if "combat_regions_v2" not in config:
        config["combat_regions_v2"] = {}

    config["combat_regions_v2"][name] = {
        "area": area,
        "kind": kind,
        "threshold": threshold,
        "enabled": enabled,
        "label": label or "",
    }

    return True, None


def delete_region(config: dict, name: str) -> tuple[bool, str | None]:
    """
    Delete a region from config["combat_regions_v2"] by name.

    Does NOT call save_config() — backend command handler does that.
    Returns (True, None) on success, (False, error_message) if not found.
    """
    regions = config.get("combat_regions_v2", {})

    if name not in regions:
        return False, f"Region not found: {name}"

    del regions[name]
    return True, None


def resolve_region(config: dict, name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a named region to absolute pixel coordinates.

    Reads game_window_title from config, calls get_window_rect() fresh each time.
    Converts normalized [x1,y1,x2,y2] area to pixel coordinates.

    Returns dict with abs_area in pixels, or None if window/region missing.
    """
    title = config.get("game_window_title")
    if not title:
        _region_log.debug("resolve_region: no game_window_title in config")
        return None

    rect = get_window_rect(title)
    if rect is None:
        _region_log.debug("resolve_region: window not found for title=%r", title)
        return None

    left, top, right, bottom = rect

    regions = config.get("combat_regions_v2", {})
    record = regions.get(name)
    if record is None:
        _region_log.debug("resolve_region: region %r not found in combat_regions_v2", name)
        return None

    record_valid, record_err = validate_region_record(name, record)
    if not record_valid:
        _region_log.warning("resolve_region: invalid region %s: %s", name, record_err)
        return None

    area = record["area"]
    width = right - left
    height = bottom - top

    abs_x1 = int(left + area[0] * width)
    abs_y1 = int(top + area[1] * height)
    abs_x2 = int(left + area[2] * width)
    abs_y2 = int(top + area[3] * height)

    return {
        "name": name,
        "abs_area": [abs_x1, abs_y1, abs_x2, abs_y2],
        "area": area,
        "kind": record.get("kind"),
        "enabled": record.get("enabled", True),
    }


def resolve_all_regions(config: dict) -> List[Dict[str, Any]]:
    """
    Resolve all regions in combat_regions_v2 to absolute pixel coordinates.

    Gets window rect once (shared across all regions) to avoid redundant calls.
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

    regions = config.get("combat_regions_v2", {})
    if not regions:
        return []

    result: List[Dict[str, Any]] = []

    for name, record in regions.items():
        record_valid, record_err = validate_region_record(name, record)
        if not record_valid:
            _region_log.warning("resolve_all_regions: skip invalid region %s: %s", name, record_err)
            continue

        area = record["area"]

        abs_x1 = int(left + area[0] * width)
        abs_y1 = int(top + area[1] * height)
        abs_x2 = int(left + area[2] * width)
        abs_y2 = int(top + area[3] * height)

        result.append({
            "name": name,
            "abs_area": [abs_x1, abs_y1, abs_x2, abs_y2],
            "area": area,
            "kind": record.get("kind"),
            "enabled": record.get("enabled", True),
        })

    return result
