from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


RUNTIME_DIR = _runtime_root()
CONFIG_FILE = str(RUNTIME_DIR / "config.json")
ASSETS_DIR = str(RUNTIME_DIR / "src" / "assets")
LOG_FILE = str(RUNTIME_DIR / "debug_log.txt")
CAPTURES_DIR = str(RUNTIME_DIR / "captures")

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
COORDINATE_LAYOUT_VERSION = 2
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
    "pos_1": [0, 0],
    "pos_2": [0, 0],
    "coordinate_layout_version": COORDINATE_LAYOUT_VERSION,
    "outcome_area": None,
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
    config["coordinate_layout_version"] = _clamp_int(
        config.get("coordinate_layout_version"), COORDINATE_LAYOUT_VERSION, 1, 99
    )
    config["outcome_area"] = _normalize_area(config.get("outcome_area"))

    config["keys"] = _deep_merge(DEFAULT_KEYS, config.get("keys", {}))
    config["images"] = _deep_merge(DEFAULT_IMAGES, config.get("images", {}))
    config["image_states"] = _deep_merge(DEFAULT_IMAGE_STATES, config.get("image_states", {}))

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

    if "coordinate_layout_version" not in user_config:
        user_config["pos_1"] = [0, 0]
        user_config["pos_2"] = [0, 0]

    user_config["coordinate_layout_version"] = COORDINATE_LAYOUT_VERSION

    config = _normalize_config(_deep_merge(DEFAULT_CONFIG, user_config))
    save_config(config)
    return config


def save_config(config):
    ensure_runtime_layout()
    normalized = _normalize_config(_deep_merge(DEFAULT_CONFIG, config))
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=4)


def set_asset_path(config, key, path_value):
    if key not in IMAGE_SPECS:
        return
    config["images"][key] = to_storage_path(path_value)
    absolute_path = resolve_path(config["images"][key])
    config["image_states"][key] = "placeholder" if _is_placeholder_asset(absolute_path) else "custom"


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
        warnings.append("Combat equip verification will fall back to slot heuristics until the Combat Equipped Indicator asset is captured.")
    return warnings
