from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


RUNTIME_DIR = _runtime_root()
CONFIG_FILE = str(RUNTIME_DIR / "config.json")
ASSETS_DIR = str(RUNTIME_DIR / "src" / "assets")
LOG_FILE = str(RUNTIME_DIR / "debug_log.txt")
CAPTURES_DIR = str(RUNTIME_DIR / "captures")

MIN_RECOMMENDED_WINDOW_SIZE = (960, 540)
WINDOW_SCALE_WARNING_DELTA = 0.18
COORDINATE_LAYOUT_VERSION = 3

IMAGE_SPECS = {
    "change": {
        "label": "Change Button",
        "description": "Lobby button used to rotate to the Battle Royale mode.",
        "filename": "change.png",
        "required": True,
    },
    "br_mode": {
        "label": "Battle Royale Mode",
        "description": "The Battle Royale mode tile/button inside the queue menu.",
        "filename": "br_mode.png",
        "required": True,
    },
    "solo_mode": {
        "label": "Solo Mode",
        "description": "The button that confirms solo queue.",
        "filename": "solo_mode.png",
        "required": True,
    },
    "return_to_lobby_alone": {
        "label": "Return To Lobby",
        "description": "The leave/return button shown when the match is active or finished.",
        "filename": "leave.png",
        "required": True,
    },
    "ultimate": {
        "label": "Ultimate Bar",
        "description": "The in-match UI element that confirms gameplay has started.",
        "filename": "ultimate.png",
        "required": True,
    },
    "combat_ready": {
        "label": "Combat Equipped Indicator",
        "description": "An in-match HUD/icon state that appears only when melee/combat is truly equipped.",
        "filename": "combat_ready.png",
        "required": False,
    },
    "open": {
        "label": "Open Button",
        "description": "End-match result screen button labelled Open.",
        "filename": "open.png",
        "required": True,
    },
    "continue": {
        "label": "Continue Button",
        "description": "End-match screen button labelled Continue.",
        "filename": "continue.png",
        "required": True,
    },
}

IMAGE_ORDER = list(IMAGE_SPECS.keys())
DEFAULT_IMAGES = {key: f"src/assets/{meta['filename']}" for key, meta in IMAGE_SPECS.items()}
DEFAULT_IMAGE_STATES = {key: "placeholder" for key in IMAGE_ORDER}
COORDINATE_SPECS = {
    "pos_1": {
        "label": "Statistics Icon",
        "description": "The Statistics icon inside the radial menu opened by the menu hotkey.",
    },
    "pos_2": {
        "label": "Melee Upgrade Button",
        "description": "The Strength/Melee upgrade button the bot should click 15 times after opening Statistics.",
    },
}
DEFAULT_KEYS = {
    "menu": "m",
    "slot_1": "1",
    "forward": "w",
    "left": "a",
    "backward": "s",
    "right": "d",
}
DEFAULT_CONFIG = {
    "game_window_title": "Grand Piece Online",
    "discord_webhook": "",
    "confidence": 0.8,
    "scan_interval": 1.5,
    "match_mode": "full",
    "movement_duration": 300,
    "window_focus_required": True,
    "auto_focus_window": True,
    "images": DEFAULT_IMAGES,
    "image_states": DEFAULT_IMAGE_STATES,
    "asset_contexts": {},
    "pos_1": [0, 0],
    "pos_2": [0, 0],
    "coordinate_profiles": {},
    "coordinate_layout_version": COORDINATE_LAYOUT_VERSION,
    "outcome_area": None,
    "outcome_area_profile": None,
    "keys": DEFAULT_KEYS,
}


def _deep_merge(base, override):
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _clamp_float(value, fallback, lower, upper):
    try:
        return max(lower, min(upper, float(value)))
    except (TypeError, ValueError):
        return fallback


def _clamp_int(value, fallback, lower, upper):
    try:
        return max(lower, min(upper, int(value)))
    except (TypeError, ValueError):
        return fallback


def _normalize_point(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return [int(value[0]), int(value[1])]
        except (TypeError, ValueError):
            return [0, 0]
    return [0, 0]


def _normalize_area(value):
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            left, top, right, bottom = [int(part) for part in value]
        except (TypeError, ValueError):
            return None
        if right > left and bottom > top:
            return [left, top, right, bottom]
    return None


def _normalize_ratio_pair(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            x = max(0.0, min(1.0, float(value[0])))
            y = max(0.0, min(1.0, float(value[1])))
            return [round(x, 6), round(y, 6)]
        except (TypeError, ValueError):
            return None
    return None


def _normalize_ratio_area(value):
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            left, top, right, bottom = [float(part) for part in value]
        except (TypeError, ValueError):
            return None
        left = max(0.0, min(1.0, left))
        top = max(0.0, min(1.0, top))
        right = max(0.0, min(1.0, right))
        bottom = max(0.0, min(1.0, bottom))
        if right > left and bottom > top:
            return [round(left, 6), round(top, 6), round(right, 6), round(bottom, 6)]
    return None


def _normalize_window_size(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            width = int(value[0])
            height = int(value[1])
        except (TypeError, ValueError):
            return None
        if width > 0 and height > 0:
            return [width, height]
    return None


def _window_size_from_rect(window_rect):
    if isinstance(window_rect, (list, tuple)) and len(window_rect) == 4:
        try:
            left, top, right, bottom = [int(part) for part in window_rect]
        except (TypeError, ValueError):
            return None
        width = right - left
        height = bottom - top
        if width > 0 and height > 0:
            return [width, height]
    return None


def _empty_coordinate_profile():
    return {
        "mode": "unbound",
        "screen": [0, 0],
        "window_relative": [0, 0],
        "window_ratio": None,
        "window_size": None,
        "window_title": "",
        "captured_at": "",
    }


def _legacy_coordinate_profile(point):
    profile = _empty_coordinate_profile()
    profile["screen"] = _normalize_point(point)
    profile["mode"] = "legacy_screen" if is_coordinate_ready(profile["screen"]) else "unbound"
    return profile


def _empty_area_profile():
    return {
        "mode": "unbound",
        "screen_area": None,
        "window_relative_area": None,
        "window_ratio_area": None,
        "window_size": None,
        "window_title": "",
        "captured_at": "",
    }


def _legacy_area_profile(area):
    profile = _empty_area_profile()
    profile["screen_area"] = _normalize_area(area)
    profile["mode"] = "legacy_screen" if profile["screen_area"] else "unbound"
    return profile


def _normalize_coordinate_profile(value, fallback_point=None):
    if isinstance(value, dict):
        screen = _normalize_point(value.get("screen", fallback_point))
        relative = _normalize_point(value.get("window_relative"))
        ratio = _normalize_ratio_pair(value.get("window_ratio"))
        window_size = _normalize_window_size(value.get("window_size"))
        mode = str(value.get("mode", "")).strip().lower()
        window_title = str(value.get("window_title", "")).strip()
        captured_at = str(value.get("captured_at", "")).strip()

        if window_size and ratio and is_coordinate_ready(screen):
            if not mode:
                mode = "window_relative"
        else:
            relative = [0, 0]
            ratio = None
            window_size = None
            mode = "legacy_screen" if is_coordinate_ready(screen) else "unbound"

        return {
            "mode": mode,
            "screen": screen,
            "window_relative": relative,
            "window_ratio": ratio,
            "window_size": window_size,
            "window_title": window_title,
            "captured_at": captured_at,
        }

    if is_coordinate_ready(fallback_point):
        return _legacy_coordinate_profile(fallback_point)
    return _empty_coordinate_profile()


def _normalize_area_profile(value, fallback_area=None):
    if isinstance(value, dict):
        screen_area = _normalize_area(value.get("screen_area", fallback_area))
        window_relative_area = _normalize_area(value.get("window_relative_area"))
        window_ratio_area = _normalize_ratio_area(value.get("window_ratio_area"))
        window_size = _normalize_window_size(value.get("window_size"))
        mode = str(value.get("mode", "")).strip().lower()
        window_title = str(value.get("window_title", "")).strip()
        captured_at = str(value.get("captured_at", "")).strip()

        if window_size and window_ratio_area and screen_area:
            if not mode:
                mode = "window_relative"
        else:
            window_relative_area = None
            window_ratio_area = None
            window_size = None
            mode = "legacy_screen" if screen_area else "unbound"

        return {
            "mode": mode,
            "screen_area": screen_area,
            "window_relative_area": window_relative_area,
            "window_ratio_area": window_ratio_area,
            "window_size": window_size,
            "window_title": window_title,
            "captured_at": captured_at,
        }

    if _normalize_area(fallback_area):
        return _legacy_area_profile(fallback_area)
    return _empty_area_profile()


def _normalize_asset_context(value):
    if not isinstance(value, dict):
        return {
            "window_size": None,
            "window_title": "",
            "captured_at": "",
            "source": "",
        }

    return {
        "window_size": _normalize_window_size(value.get("window_size")),
        "window_title": str(value.get("window_title", "")).strip(),
        "captured_at": str(value.get("captured_at", "")).strip(),
        "source": str(value.get("source", "")).strip(),
    }


def describe_window_size(value) -> str:
    size = _normalize_window_size(value)
    if size:
        return f"{size[0]}x{size[1]}"

    rect_size = _window_size_from_rect(value)
    if rect_size:
        return f"{rect_size[0]}x{rect_size[1]}"
    return "unknown size"


def estimate_window_scale_delta(source_size, current_size):
    source = _normalize_window_size(source_size)
    current = _normalize_window_size(current_size)
    if not source or not current:
        return None
    width_ratio = current[0] / max(1, source[0])
    height_ratio = current[1] / max(1, source[1])
    return max(abs(width_ratio - 1.0), abs(height_ratio - 1.0))


def point_inside_window(point, window_rect, margin=0):
    normalized_point = _normalize_point(point)
    if not is_coordinate_ready(normalized_point):
        return False

    if not isinstance(window_rect, (list, tuple)) or len(window_rect) != 4:
        return False

    left, top, right, bottom = [int(part) for part in window_rect]
    return (
        left + margin <= normalized_point[0] <= right - 1 - margin
        and top + margin <= normalized_point[1] <= bottom - 1 - margin
    )


def resolve_path(path_value: str | None) -> str:
    if not path_value:
        return ""
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str((RUNTIME_DIR / path).resolve())


def to_storage_path(path_value: str | None) -> str:
    if not path_value:
        return ""
    path = Path(path_value).resolve()
    try:
        relative = path.relative_to(RUNTIME_DIR)
        return relative.as_posix()
    except ValueError:
        try:
            return os.path.relpath(str(path), str(RUNTIME_DIR)).replace("\\", "/")
        except ValueError:
            return str(path)


def _is_placeholder_asset(path_value: str) -> bool:
    try:
        with Image.open(path_value) as img:
            for info_key, info_value in img.info.items():
                if str(info_key).endswith("_placeholder") and str(info_value) == "1":
                    return True
            return False
    except Exception:
        return False


def _create_placeholder_asset(key: str, path_value: str):
    meta = IMAGE_SPECS[key]
    Path(path_value).parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (360, 160), "#0f172a")
    draw = ImageDraw.Draw(img)
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()

    draw.rounded_rectangle((12, 12, 348, 148), radius=16, outline="#60a5fa", width=3, fill="#111827")
    draw.rectangle((24, 24, 336, 48), fill="#1d4ed8")
    draw.text((36, 30), meta["label"], fill="white", font=font_large)
    draw.text((36, 72), "Placeholder asset", fill="#f8fafc", font=font_small)
    draw.text((36, 96), "Capture the real in-game button from the app.", fill="#cbd5e1", font=font_small)
    draw.text((36, 118), f"Target file: {meta['filename']}", fill="#93c5fd", font=font_small)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("zedsu_placeholder", "1")
    pnginfo.add_text("zedsu_asset_key", key)
    img.save(path_value, pnginfo=pnginfo)


def ensure_runtime_layout():
    Path(ASSETS_DIR).mkdir(parents=True, exist_ok=True)
    Path(CAPTURES_DIR).mkdir(parents=True, exist_ok=True)


def _normalize_config(config):
    config["game_window_title"] = str(config.get("game_window_title", "")).strip()
    config["discord_webhook"] = str(config.get("discord_webhook", "")).strip()
    config["confidence"] = _clamp_float(config.get("confidence"), 0.8, 0.1, 1.0)
    config["scan_interval"] = _clamp_float(config.get("scan_interval"), 1.5, 0.2, 10.0)
    config["movement_duration"] = _clamp_int(config.get("movement_duration"), 300, 30, 3600)
    config["match_mode"] = "quick" if config.get("match_mode") == "quick" else "full"
    config["window_focus_required"] = bool(config.get("window_focus_required", True))
    config["auto_focus_window"] = bool(config.get("auto_focus_window", True))
    config["pos_1"] = _normalize_point(config.get("pos_1"))
    config["pos_2"] = _normalize_point(config.get("pos_2"))
    config["coordinate_layout_version"] = COORDINATE_LAYOUT_VERSION
    config["outcome_area"] = _normalize_area(config.get("outcome_area"))

    config["keys"] = _deep_merge(DEFAULT_KEYS, config.get("keys", {}))
    config["images"] = _deep_merge(DEFAULT_IMAGES, config.get("images", {}))
    config["image_states"] = _deep_merge(DEFAULT_IMAGE_STATES, config.get("image_states", {}))

    raw_profiles = config.get("coordinate_profiles", {})
    config["coordinate_profiles"] = {
        key: _normalize_coordinate_profile(raw_profiles.get(key), fallback_point=config.get(key))
        for key in COORDINATE_SPECS
    }
    config["outcome_area_profile"] = _normalize_area_profile(
        config.get("outcome_area_profile"),
        fallback_area=config.get("outcome_area"),
    )

    raw_asset_contexts = config.get("asset_contexts", {})
    config["asset_contexts"] = {
        key: _normalize_asset_context(raw_asset_contexts.get(key))
        for key in IMAGE_ORDER
    }

    for key in IMAGE_ORDER:
        raw_path = config["images"].get(key) or DEFAULT_IMAGES[key]
        absolute_path = resolve_path(raw_path)

        if not os.path.exists(absolute_path):
            _create_placeholder_asset(key, absolute_path)
            config["images"][key] = to_storage_path(absolute_path)
            config["image_states"][key] = "placeholder"
            continue

        config["images"][key] = to_storage_path(absolute_path)
        config["image_states"][key] = "placeholder" if _is_placeholder_asset(absolute_path) else "custom"

    return config


def load_config():
    ensure_runtime_layout()
    user_config = {}

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                user_config = json.load(file)
        except Exception:
            user_config = {}

    user_config.setdefault("coordinate_profiles", {})
    for key in COORDINATE_SPECS:
        if key not in user_config["coordinate_profiles"] and is_coordinate_ready(user_config.get(key)):
            user_config["coordinate_profiles"][key] = _legacy_coordinate_profile(user_config.get(key))

    if "outcome_area_profile" not in user_config and _normalize_area(user_config.get("outcome_area")):
        user_config["outcome_area_profile"] = _legacy_area_profile(user_config.get("outcome_area"))

    user_config.setdefault("asset_contexts", {})
    user_config["coordinate_layout_version"] = COORDINATE_LAYOUT_VERSION

    config = _normalize_config(_deep_merge(DEFAULT_CONFIG, user_config))
    save_config(config)
    return config


def save_config(config):
    ensure_runtime_layout()
    normalized = _normalize_config(_deep_merge(DEFAULT_CONFIG, config))
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=4)


def get_coordinate_profile(config, key):
    return _normalize_coordinate_profile(
        (config or {}).get("coordinate_profiles", {}).get(key),
        fallback_point=(config or {}).get(key),
    )


def set_coordinate_binding(config, key, screen_point, window_rect=None, window_title=""):
    if key not in COORDINATE_SPECS:
        return

    point = _normalize_point(screen_point)
    config[key] = point
    profile = _legacy_coordinate_profile(point)
    current_window_size = _window_size_from_rect(window_rect)

    if current_window_size and is_coordinate_ready(point):
        left, top, right, bottom = [int(part) for part in window_rect]
        width = max(1, right - left)
        height = max(1, bottom - top)
        relative_x = point[0] - left
        relative_y = point[1] - top
        if 0 <= relative_x < width and 0 <= relative_y < height:
            profile = {
                "mode": "window_relative",
                "screen": point,
                "window_relative": [int(relative_x), int(relative_y)],
                "window_ratio": [
                    round(relative_x / width, 6),
                    round(relative_y / height, 6),
                ],
                "window_size": current_window_size,
                "window_title": str(window_title or "").strip(),
                "captured_at": _utc_timestamp(),
            }

    config.setdefault("coordinate_profiles", {})[key] = profile
    config["coordinate_layout_version"] = COORDINATE_LAYOUT_VERSION


def resolve_coordinate(config, key, window_rect=None):
    profile = get_coordinate_profile(config, key)
    screen_point = _normalize_point((config or {}).get(key) or profile.get("screen"))

    if profile.get("mode") == "window_relative" and profile.get("window_ratio") and window_rect:
        current_window_size = _window_size_from_rect(window_rect)
        if current_window_size:
            left, top, right, bottom = [int(part) for part in window_rect]
            width = max(1, right - left)
            height = max(1, bottom - top)
            ratio_x, ratio_y = profile["window_ratio"]
            x = left + min(width - 1, max(0, int(round(ratio_x * width))))
            y = top + min(height - 1, max(0, int(round(ratio_y * height))))
            return [x, y]

    return screen_point


def describe_coordinate_binding(config, key):
    profile = get_coordinate_profile(config, key)
    point = _normalize_point((config or {}).get(key) or profile.get("screen"))
    if not is_coordinate_ready(point):
        return "Binding: not set."

    if profile.get("mode") == "window_relative" and profile.get("window_size"):
        return (
            "Binding: portable window-relative capture"
            f" ({describe_window_size(profile['window_size'])})."
        )
    return "Binding: legacy screen coordinate. Re-pick on each machine or Roblox size change."


def set_outcome_area_binding(config, absolute_area, window_rect=None, window_title=""):
    area = _normalize_area(absolute_area)
    config["outcome_area"] = area
    profile = _legacy_area_profile(area)
    current_window_size = _window_size_from_rect(window_rect)

    if area and current_window_size:
        left, top, right, bottom = [int(part) for part in window_rect]
        width = max(1, right - left)
        height = max(1, bottom - top)
        relative_area = [
            area[0] - left,
            area[1] - top,
            area[2] - left,
            area[3] - top,
        ]
        if (
            0 <= relative_area[0] < width
            and 0 <= relative_area[1] < height
            and 0 < relative_area[2] <= width
            and 0 < relative_area[3] <= height
            and relative_area[2] > relative_area[0]
            and relative_area[3] > relative_area[1]
        ):
            profile = {
                "mode": "window_relative",
                "screen_area": area,
                "window_relative_area": [int(value) for value in relative_area],
                "window_ratio_area": [
                    round(relative_area[0] / width, 6),
                    round(relative_area[1] / height, 6),
                    round(relative_area[2] / width, 6),
                    round(relative_area[3] / height, 6),
                ],
                "window_size": current_window_size,
                "window_title": str(window_title or "").strip(),
                "captured_at": _utc_timestamp(),
            }

    config["outcome_area_profile"] = profile
    config["coordinate_layout_version"] = COORDINATE_LAYOUT_VERSION


def resolve_outcome_area(config, window_rect=None):
    profile = _normalize_area_profile(
        (config or {}).get("outcome_area_profile"),
        fallback_area=(config or {}).get("outcome_area"),
    )
    area = _normalize_area((config or {}).get("outcome_area") or profile.get("screen_area"))
    if profile.get("mode") == "window_relative" and profile.get("window_ratio_area") and window_rect:
        left, top, right, bottom = [int(part) for part in window_rect]
        width = max(1, right - left)
        height = max(1, bottom - top)
        r_left, r_top, r_right, r_bottom = profile["window_ratio_area"]
        resolved = [
            left + min(width - 1, max(0, int(round(r_left * width)))),
            top + min(height - 1, max(0, int(round(r_top * height)))),
            left + min(width, max(1, int(round(r_right * width)))),
            top + min(height, max(1, int(round(r_bottom * height)))),
        ]
        normalized = _normalize_area(resolved)
        if normalized:
            return normalized
    return area


def describe_area_binding(config):
    area = resolve_outcome_area(config)
    profile = _normalize_area_profile(
        (config or {}).get("outcome_area_profile"),
        fallback_area=(config or {}).get("outcome_area"),
    )
    if not area:
        return "Area: full screen"
    if profile.get("mode") == "window_relative" and profile.get("window_size"):
        return (
            f"Area: {area} | portable window-relative capture"
            f" ({describe_window_size(profile['window_size'])})"
        )
    return f"Area: {area} | legacy screen area"


def get_asset_capture_context(config, key):
    return _normalize_asset_context((config or {}).get("asset_contexts", {}).get(key))


def set_asset_capture_context(config, key, window_rect=None, window_title="", source=""):
    if key not in IMAGE_SPECS:
        return
    context = {
        "window_size": _window_size_from_rect(window_rect),
        "window_title": str(window_title or "").strip(),
        "captured_at": _utc_timestamp(),
        "source": str(source or "").strip(),
    }
    config.setdefault("asset_contexts", {})[key] = context


def set_asset_path(config, key, path_value, window_rect=None, window_title="", capture_source=""):
    if key not in IMAGE_SPECS:
        return
    config["images"][key] = to_storage_path(path_value)
    absolute_path = resolve_path(config["images"][key])
    config["image_states"][key] = "placeholder" if _is_placeholder_asset(absolute_path) else "custom"
    if window_rect:
        set_asset_capture_context(config, key, window_rect=window_rect, window_title=window_title, source=capture_source)
    else:
        config.setdefault("asset_contexts", {})[key] = _normalize_asset_context({})


def get_asset_record(config, key):
    path_value = config["images"].get(key, DEFAULT_IMAGES[key])
    absolute_path = resolve_path(path_value)
    state = config.get("image_states", {}).get(key, "missing")
    if not os.path.exists(absolute_path):
        state = "missing"

    return {
        "key": key,
        "label": IMAGE_SPECS[key]["label"],
        "description": IMAGE_SPECS[key]["description"],
        "filename": IMAGE_SPECS[key]["filename"],
        "path": path_value,
        "absolute_path": absolute_path,
        "state": state,
        "required": bool(IMAGE_SPECS[key].get("required", True)),
    }


def get_asset_records(config):
    return [get_asset_record(config, key) for key in IMAGE_ORDER]


def get_required_asset_records(config):
    return [record for record in get_asset_records(config) if record["required"]]


def get_optional_asset_records(config):
    return [record for record in get_asset_records(config) if not record["required"]]


def is_asset_custom(config, key):
    record = get_asset_record(config, key)
    return record["state"] == "custom"


def is_coordinate_ready(point):
    return isinstance(point, (list, tuple)) and len(point) == 2 and any(int(part) != 0 for part in point)


def get_runtime_portability_report(config, window_rect=None):
    current_window_size = _window_size_from_rect(window_rect)
    warnings = []
    blockers = []
    legacy_coordinate_keys = []
    scaled_asset_keys = []

    if current_window_size:
        if (
            current_window_size[0] < MIN_RECOMMENDED_WINDOW_SIZE[0]
            or current_window_size[1] < MIN_RECOMMENDED_WINDOW_SIZE[1]
        ):
            warnings.append(
                "Roblox is running below the recommended client size "
                f"({describe_window_size(current_window_size)}). Detection can still work, but smaller HUD elements are less reliable."
            )

    for key, meta in COORDINATE_SPECS.items():
        resolved = resolve_coordinate(config, key, window_rect=window_rect)
        if not is_coordinate_ready(resolved):
            continue

        profile = get_coordinate_profile(config, key)
        if profile.get("mode") != "window_relative":
            legacy_coordinate_keys.append(key)

        if window_rect and not point_inside_window(resolved, window_rect, margin=1):
            blockers.append(
                f"{meta['label']} resolves outside the current Roblox client. Re-pick it before starting the bot."
            )
            continue

        if current_window_size and profile.get("window_size"):
            delta = estimate_window_scale_delta(profile["window_size"], current_window_size)
            if delta is not None and delta >= 0.35 and profile.get("mode") == "window_relative":
                warnings.append(
                    f"{meta['label']} was captured at {describe_window_size(profile['window_size'])}. "
                    f"The current client is {describe_window_size(current_window_size)}. Window-relative clicks will scale, "
                    "but a fresh pick is safer for perfect alignment."
                )

    if legacy_coordinate_keys:
        names = ", ".join(COORDINATE_SPECS[key]["label"] for key in legacy_coordinate_keys)
        warnings.append(
            f"Portable coordinate binding is incomplete. Re-pick these on-screen controls to make them follow the Roblox window: {names}."
        )

    outcome_profile = _normalize_area_profile(
        config.get("outcome_area_profile"),
        fallback_area=config.get("outcome_area"),
    )
    if outcome_profile.get("screen_area") and outcome_profile.get("mode") != "window_relative":
        warnings.append(
            "Result screenshot area is using a legacy screen crop. Re-pick it if you move Roblox to another monitor or resize the client."
        )

    if current_window_size:
        for key in IMAGE_ORDER:
            if not is_asset_custom(config, key):
                continue
            context = get_asset_capture_context(config, key)
            if not context.get("window_size"):
                continue
            delta = estimate_window_scale_delta(context["window_size"], current_window_size)
            if delta is not None and delta >= WINDOW_SCALE_WARNING_DELTA:
                scaled_asset_keys.append(key)

    return {
        "window_size": current_window_size,
        "warnings": warnings,
        "blockers": blockers,
        "legacy_coordinate_keys": legacy_coordinate_keys,
        "scaled_asset_keys": scaled_asset_keys,
    }


def get_required_setup_issues(config):
    issues = []

    if not str(config.get("game_window_title", "")).strip():
        issues.append("Set the game window title before starting the bot.")

    placeholders = [record["label"] for record in get_required_asset_records(config) if record["state"] != "custom"]
    if placeholders:
        issues.append(f"Capture or choose all assets first: {', '.join(placeholders)}.")

    if not is_coordinate_ready(config.get("pos_1")):
        issues.append(f"Set the {COORDINATE_SPECS['pos_1']['label']} coordinate used by the combat setup.")

    if not is_coordinate_ready(config.get("pos_2")):
        issues.append(f"Set the {COORDINATE_SPECS['pos_2']['label']} coordinate used by the combat setup.")

    webhook = str(config.get("discord_webhook", "")).strip()
    if webhook and not webhook.startswith("https://discord.com/api/webhooks/"):
        issues.append("Discord webhook must start with https://discord.com/api/webhooks/.")

    return issues


def get_optional_setup_warnings(config):
    warnings = []
    if not config.get("discord_webhook"):
        warnings.append("Discord webhook is empty. Match notifications will stay local only.")
    if not config.get("outcome_area"):
        warnings.append("Result screenshots will use the full screen until a capture area is set.")
    if not is_asset_custom(config, "combat_ready"):
        warnings.append(
            "Combat equip verification will fall back to slot heuristics until the Combat Equipped Indicator asset is captured."
        )
    return warnings
