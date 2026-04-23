import os
import time
import tkinter as tk
from collections import namedtuple

import pyautogui
from PIL import Image, ImageEnhance, ImageTk

try:
    import mss
    import numpy as np
    import cv2
    _MSS_AVAILABLE = True
    _CV2_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False
    _CV2_AVAILABLE = False
    np = None
    cv2 = None

# Reusable box type shared by _cv2_locate_image
_Box = namedtuple("Box", ["left", "top", "width", "height"])

from src.core.controller import human_click
from src.utils.config import get_asset_capture_context, resolve_path
from src.utils.windows import get_window_rect


_IMAGE_CACHE = {}
_SCALED_IMAGE_CACHE = {}
_SCALE_HINT_CACHE = {}
_LAST_MATCH_REGION_CACHE = {}
_LAST_MATCH_MAX_AGE = 180.0
_SEARCH_HINT_RATIOS = {
    "ultimate": ((0.18, 0.64, 0.84, 1.0),),
    "open": ((0.16, 0.35, 0.86, 0.98),),
    "continue": ((0.16, 0.35, 0.86, 0.98),),
    "return_to_lobby_alone": ((0.08, 0.2, 0.92, 0.96),),
    "solo_mode": ((0.12, 0.08, 0.9, 0.9),),
    "br_mode": ((0.12, 0.08, 0.9, 0.9),),
    "change": ((0.02, 0.02, 0.9, 0.72),),
}


def _normalize_region(region):
    if not region or len(region) != 4:
        return None

    left, top, right, bottom = [int(value) for value in region]
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None
    return left, top, width, height


def _region_size(region):
    if not region or len(region) != 4:
        return None
    left, top, right, bottom = [int(value) for value in region]
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None
    return [width, height]


def _load_template(path):
    modified = os.path.getmtime(path)
    cache_entry = _IMAGE_CACHE.get(path)
    if cache_entry and cache_entry["mtime"] == modified:
        return cache_entry["image"]

    with Image.open(path) as image:
        loaded = image.convert("RGB")

    _IMAGE_CACHE[path] = {"mtime": modified, "image": loaded}
    stale_keys = [key for key in _SCALED_IMAGE_CACHE if key[0] == path and key[1] != modified]
    for stale_key in stale_keys:
        _SCALED_IMAGE_CACHE.pop(stale_key, None)
    return loaded


def _scaled_template(path, scale):
    base_image = _load_template(path)
    modified = os.path.getmtime(path)
    rounded_scale = round(float(scale), 4)
    cache_key = (path, modified, rounded_scale)

    cached = _SCALED_IMAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if abs(rounded_scale - 1.0) < 0.01:
        _SCALED_IMAGE_CACHE[cache_key] = base_image
        return base_image

    width = max(1, int(round(base_image.width * rounded_scale)))
    height = max(1, int(round(base_image.height * rounded_scale)))
    resized = base_image.resize((width, height), Image.Resampling.LANCZOS)
    _SCALED_IMAGE_CACHE[cache_key] = resized
    return resized


def _capture_haystack(normalized_region):
    try:
        if normalized_region:
            left, top, width, height = normalized_region
            return pyautogui.screenshot(region=(left, top, width, height)).convert("RGB"), (left, top)
        return pyautogui.screenshot().convert("RGB"), (0, 0)
    except Exception:
        return None, (0, 0)


def _mss_capture_haystack(normalized_region):
    """Fast screen capture using MSS. Returns (RGB numpy array, offset) tuple."""
    if not _MSS_AVAILABLE or np is None:
        return None, (0, 0)
    try:
        with mss.mss() as sct:
            if normalized_region:
                left, top, width, height = [int(v) for v in normalized_region]
            else:
                left, top = 0, 0
                width, height = sct.monitors[1]["width"], sct.monitors[1]["height"]

            monitor = {"left": left, "top": top, "width": width, "height": height}
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            if img.shape[2] == 4:
                img = img[:, :, :3][:, :, ::-1]  # BGRA -> RGB
            return img, (left, top)
    except Exception:
        return None, (0, 0)


def _hsv_prefilter(img_name, config, region=None, search_context=None):
    """Layer 1: fast HSV color pre-filter. Returns True if color present, None to skip, False if absent."""
    if not _MSS_AVAILABLE or np is None or cv2 is None:
        return None

    hsv_settings = (config.get("hsv_settings") or {}).get(img_name)
    if not hsv_settings or not hsv_settings.get("enabled"):
        return None

    h_min = int(hsv_settings.get("h_min", 0))
    h_max = int(hsv_settings.get("h_max", 179))
    s_min = int(hsv_settings.get("s_min", 0))
    s_max = int(hsv_settings.get("s_max", 255))
    v_min = int(hsv_settings.get("v_min", 0))
    v_max = int(hsv_settings.get("v_max", 255))

    # Use provided search context or capture fresh
    if search_context and search_context.get("image") is not None:
        haystack_rgb = search_context["image"]
        offset = search_context.get("offset", (0, 0))
        bounds = search_context.get("region")
    else:
        window_title = config.get("game_window_title", "")
        if region:
            normalized = _normalize_region(region) if isinstance(region, (tuple, list)) else None
        elif window_title:
            region_rect = get_window_rect(str(window_title))
            normalized = _normalize_region(region_rect) if region_rect else None
        else:
            normalized = None

        haystack_rgb, offset = _mss_capture_haystack(normalized)
        if haystack_rgb is None:
            return False
        bounds = (
            (offset[0], offset[1],
             offset[0] + haystack_rgb.shape[1],
             offset[1] + haystack_rgb.shape[0])
            if normalized
            else None
        )

    # Restrict search to the hint region for this asset
    search_area = None
    if bounds:
        for ratio_region in _SEARCH_HINT_RATIOS.get(img_name, ()):
            search_area = _region_from_ratio_area(ratio_region, bounds)
            if search_area:
                break

    if search_area:
        bx0, by0, bx1, by1 = search_area
        # Clamp to image bounds
        h, w = haystack_rgb.shape[:2]
        x0 = max(0, min(w, bx0))
        y0 = max(0, min(h, by0))
        x1 = max(0, min(w, bx1))
        y1 = max(0, min(h, by1))
        if x1 > x0 and y1 > y0:
            haystack_rgb = haystack_rgb[y0:y1, x0:x1]

    # BGR -> HSV
    hsv = cv2.cvtColor(haystack_rgb, cv2.COLOR_RGB2HSV)

    # Handle hue wrap-around: if h_min > h_max, the range crosses 0 (red wrap)
    if h_min <= h_max:
        mask = cv2.inRange(hsv, np.array([h_min, s_min, v_min]), np.array([h_max, s_max, v_max]))
    else:
        mask1 = cv2.inRange(hsv, np.array([0, s_min, v_min]), np.array([h_max, s_max, v_max]))
        mask2 = cv2.inRange(hsv, np.array([h_min, s_min, v_min]), np.array([179, s_max, v_max]))
        mask = mask1 | mask2

    ratio = cv2.countNonZero(mask) / max(1, mask.size)
    return ratio >= 0.003


# Global window scale reference (used by Phase 7 window resize detection)
_WINDOW_CAPTURE_WIDTH = None
_WINDOW_CAPTURE_HEIGHT = None
_WINDOW_SCALE_FACTOR = 1.0


def _region_from_normalized(normalized_region, image=None, offset=(0, 0)):
    if normalized_region:
        left, top, width, height = normalized_region
        return (int(left), int(top), int(left + width), int(top + height))
    if image is None:
        return None
    offset_x, offset_y = offset
    return (int(offset_x), int(offset_y), int(offset_x + image.width), int(offset_y + image.height))


def _clamp_region(region, bounds):
    if not region or not bounds:
        return None

    left = max(int(bounds[0]), int(region[0]))
    top = max(int(bounds[1]), int(region[1]))
    right = min(int(bounds[2]), int(region[2]))
    bottom = min(int(bounds[3]), int(region[3]))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def _expand_region(region, bounds, padding_x, padding_y):
    if not region:
        return None
    expanded = (
        int(region[0] - padding_x),
        int(region[1] - padding_y),
        int(region[2] + padding_x),
        int(region[3] + padding_y),
    )
    return _clamp_region(expanded, bounds)


def _ratio_area(region, bounds):
    if not region or not bounds:
        return None

    width = max(1, int(bounds[2] - bounds[0]))
    height = max(1, int(bounds[3] - bounds[1]))
    left = (int(region[0]) - int(bounds[0])) / width
    top = (int(region[1]) - int(bounds[1])) / height
    right = (int(region[2]) - int(bounds[0])) / width
    bottom = (int(region[3]) - int(bounds[1])) / height

    left = max(0.0, min(1.0, left))
    top = max(0.0, min(1.0, top))
    right = max(0.0, min(1.0, right))
    bottom = max(0.0, min(1.0, bottom))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def _region_from_ratio_area(ratio_area, bounds):
    if not ratio_area or not bounds:
        return None

    width = max(1, int(bounds[2] - bounds[0]))
    height = max(1, int(bounds[3] - bounds[1]))
    left = int(bounds[0] + (ratio_area[0] * width))
    top = int(bounds[1] + (ratio_area[1] * height))
    right = int(bounds[0] + (ratio_area[2] * width))
    bottom = int(bounds[1] + (ratio_area[3] * height))
    return _clamp_region((left, top, right, bottom), bounds)


def _crop_search_context(search_context, region):
    image = search_context.get("image")
    bounds = search_context.get("region")
    if image is None or not bounds:
        return None, (0, 0)

    cropped_region = _clamp_region(region, bounds)
    if not cropped_region:
        return None, (0, 0)

    if cropped_region == bounds:
        return image, (bounds[0], bounds[1])

    local_left = int(cropped_region[0] - bounds[0])
    local_top = int(cropped_region[1] - bounds[1])
    local_right = int(cropped_region[2] - bounds[0])
    local_bottom = int(cropped_region[3] - bounds[1])
    return image.crop((local_left, local_top, local_right, local_bottom)), (cropped_region[0], cropped_region[1])


def _box_to_region(box):
    return (int(box.left), int(box.top), int(box.left + box.width), int(box.top + box.height))


def _register_last_match(img_name, box, search_context):
    bounds = search_context.get("region")
    match_region = _box_to_region(box)
    ratio = _ratio_area(match_region, bounds)
    if ratio:
        _LAST_MATCH_REGION_CACHE[img_name] = {"ratio_area": ratio, "updated_at": time.time()}


def _iter_candidate_regions(img_name, search_context):
    bounds = search_context.get("region")
    if not bounds:
        return []

    candidates = []
    cached = _LAST_MATCH_REGION_CACHE.get(img_name)
    if cached and (time.time() - cached.get("updated_at", 0)) <= _LAST_MATCH_MAX_AGE:
        cached_region = _region_from_ratio_area(cached.get("ratio_area"), bounds)
        if cached_region:
            cached_width = max(1, cached_region[2] - cached_region[0])
            cached_height = max(1, cached_region[3] - cached_region[1])
            candidates.append(
                _expand_region(
                    cached_region,
                    bounds,
                    max(42, int(cached_width * 1.8)),
                    max(28, int(cached_height * 1.8)),
                )
            )

    for ratio_region in _SEARCH_HINT_RATIOS.get(img_name, ()):
        candidates.append(_region_from_ratio_area(ratio_region, bounds))

    candidates.append(bounds)

    unique = []
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = tuple(int(value) for value in candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def capture_search_context(region=None):
    normalized_region = _normalize_region(region)
    image, offset = _capture_haystack(normalized_region)
    current_size = _region_size(region)
    if image is None:
        return {
            "image": None,
            "offset": offset,
            "normalized_region": normalized_region,
            "region": None,
            "current_size": current_size,
        }

    return {
        "image": image,
        "offset": offset,
        "normalized_region": normalized_region,
        "region": _region_from_normalized(normalized_region, image=image, offset=offset),
        "current_size": current_size or [image.width, image.height],
    }


def _build_scale_candidates(img_name, config, current_size):
    candidates = []
    hinted_scale = _SCALE_HINT_CACHE.get(img_name)
    if hinted_scale:
        candidates.append(hinted_scale)

    asset_context = get_asset_capture_context(config, img_name)
    capture_size = asset_context.get("window_size")
    if capture_size and current_size:
        ratio_w = current_size[0] / max(1, capture_size[0])
        ratio_h = current_size[1] / max(1, capture_size[1])
        anchor = max(0.6, min(1.5, (ratio_w + ratio_h) / 2.0))
        candidates.extend([anchor, anchor * 0.97, anchor * 1.03])
        if abs(anchor - 1.0) >= 0.16:
            candidates.extend([anchor * 0.92, anchor * 1.08])

    candidates.extend([1.0, 0.94, 1.06])

    unique = []
    for scale in candidates:
        normalized = max(0.6, min(1.5, round(float(scale), 4)))
        if all(abs(normalized - existing) >= 0.015 for existing in unique):
            unique.append(normalized)
        if len(unique) >= 6:
            break
    return unique


def _cv2_locate_image(img_name, config, confidence=None, region=None, search_context=None):
    """Fast image location using cv2.matchTemplate + MSS capture."""
    if not _MSS_AVAILABLE:
        return None

    path = resolve_path(config.get("images", {}).get(img_name))
    if not path or not os.path.exists(path):
        return None

    conf = float(confidence if confidence is not None else config.get("confidence", 0.8))
    window_title = config.get("game_window_title", "")

    # Capture screen using MSS
    region_rect = get_window_rect(str(window_title)) if window_title else None
    if region_rect:
        normalized = _normalize_region(region_rect)
    elif region:
        normalized = _normalize_region(region) if isinstance(region, (tuple, list)) else None
    else:
        normalized = None

    haystack_rgb, offset = _mss_capture_haystack(normalized)
    if haystack_rgb is None:
        return None

    # Update window capture dimensions
    global _WINDOW_CAPTURE_WIDTH, _WINDOW_CAPTURE_HEIGHT
    if normalized and len(normalized) == 4:
        _WINDOW_CAPTURE_WIDTH = normalized[2]
        _WINDOW_CAPTURE_HEIGHT = normalized[3]

    # Convert RGB -> BGR for cv2
    haystack_bgr = haystack_rgb[:, :, ::-1]
    haystack_gray = cv2.cvtColor(haystack_bgr, cv2.COLOR_BGR2GRAY)

    current_size = [haystack_rgb.shape[1], haystack_rgb.shape[0]]
    scales = _build_scale_candidates(img_name, config, current_size)

    attempts = [
        {"grayscale": True, "conf": conf},
        {"grayscale": False, "conf": max(0.58, conf - 0.04)},
        {"grayscale": False, "conf": max(0.5, conf - 0.12)},
    ]

    # Load needle as numpy array
    needle_img = _load_template(path)
    needle_rgb = np.array(needle_img)

    for scale in scales[:6]:
        # Scale needle
        scaled_w = max(1, int(round(needle_rgb.shape[1] * scale)))
        scaled_h = max(1, int(round(needle_rgb.shape[0] * scale)))
        needle_scaled = cv2.resize(needle_rgb, (scaled_w, scaled_h), interpolation=cv2.INTER_LINEAR)

        if needle_scaled.shape[0] > haystack_gray.shape[0] or needle_scaled.shape[1] > haystack_gray.shape[1]:
            continue

        for attempt in attempts:
            try:
                if attempt["grayscale"]:
                    needle_attempt = cv2.cvtColor(needle_scaled, cv2.COLOR_RGB2GRAY)
                else:
                    needle_attempt = cv2.cvtColor(needle_scaled, cv2.COLOR_RGB2GRAY)  # cv2.matchTemplate needs grayscale

                result = cv2.matchTemplate(
                    haystack_gray, needle_attempt, cv2.TM_CCOEFF_NORMED
                )
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val >= attempt["conf"]:
                    _SCALE_HINT_CACHE[img_name] = scale

                    box = _Box(
                        left=max_loc[0] + offset[0],
                        top=max_loc[1] + offset[1],
                        width=scaled_w,
                        height=scaled_h,
                    )

                    # Build active_context for _register_last_match
                    active_context = {
                        "region": (offset[0], offset[1],
                                   offset[0] + haystack_rgb.shape[1],
                                   offset[1] + haystack_rgb.shape[0]),
                        "image": haystack_rgb,
                    }
                    _register_last_match(img_name, box, active_context)
                    return box
            except Exception:
                continue

    return None


def _offset_box(result, offset_x, offset_y):
    if offset_x == 0 and offset_y == 0:
        return result
    return type(result)(
        int(result.left + offset_x),
        int(result.top + offset_y),
        int(result.width),
        int(result.height),
    )


def locate_image(img_name, config, confidence=None, region=None, search_context=None):
    path = resolve_path(config.get("images", {}).get(img_name))
    if not path or not os.path.exists(path):
        return None

    # Layer 1: HSV pre-filter (fast color check before expensive template match)
    hsv_result = _hsv_prefilter(img_name, config, region, search_context)
    if hsv_result is False:
        return None  # Color definitely absent — skip template matching

    backend = config.get("detection_backend", "auto")
    if backend == "auto":
        backend = "opencv" if _MSS_AVAILABLE else "pyautogui"

    if backend == "opencv" and _MSS_AVAILABLE:
        return _cv2_locate_image(img_name, config, confidence, region, search_context)

    # pyautogui fallback
    conf = float(confidence if confidence is not None else config.get("confidence", 0.8))
    active_context = search_context or capture_search_context(region)
    current_size = active_context.get("current_size") or _region_size(region)
    if active_context.get("image") is None:
        return None

    attempts = (
        {"grayscale": True, "confidence": conf},
        {"grayscale": False, "confidence": max(0.58, conf - 0.04)},
        {"grayscale": False, "confidence": max(0.5, conf - 0.12)},
    )

    for candidate_region in _iter_candidate_regions(img_name, active_context):
        haystack, offset = _crop_search_context(active_context, candidate_region)
        if haystack is None:
            continue

        haystack_width, haystack_height = haystack.size
        for scale in _build_scale_candidates(img_name, config, current_size):
            needle = _scaled_template(path, scale)
            if needle.width > haystack_width or needle.height > haystack_height:
                continue

            for attempt in attempts:
                try:
                    result = pyautogui.locate(
                        needle,
                        haystack,
                        grayscale=attempt["grayscale"],
                        confidence=attempt["confidence"],
                    )
                except Exception:
                    result = None

                if result:
                    _SCALE_HINT_CACHE[img_name] = scale
                    absolute_result = _offset_box(result, offset[0], offset[1])
                    _register_last_match(img_name, absolute_result, active_context)
                    return absolute_result

    return None


def is_image_visible(img_name, config, confidence=None, region=None, search_context=None):
    return locate_image(
        img_name,
        config,
        confidence=confidence,
        region=region,
        search_context=search_context,
    ) is not None


def find_and_click(
    img_name,
    config,
    is_running_check,
    log_func,
    clicks=1,
    region=None,
    confidence=None,
    search_context=None,
):
    if not is_running_check():
        return False

    pos = locate_image(
        img_name,
        config,
        confidence=confidence,
        region=region,
        search_context=search_context,
    )
    if not pos:
        return False

    center = pyautogui.center(pos)
    safe_offset = min(10, max(2, min(pos.width, pos.height) // 4))
    log_func(f"Detected {img_name}.")

    if not human_click(center.x, center.y, is_running_check, move=True, offset=safe_offset):
        return False

    for _ in range(max(0, clicks - 1)):
        if not human_click(center.x, center.y, is_running_check, move=False):
            return False
    return True


class ScreenCaptureTool:
    def __init__(
        self,
        parent,
        screenshot,
        key,
        assets_dir,
        on_complete,
        on_cancel=None,
        save_name=None,
        title=None,
    ):
        self.parent = parent
        self.screenshot = screenshot
        self.key = key
        self.assets_dir = assets_dir
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.save_name = save_name or f"{key}.png"
        self.title = title or key.replace("_", " ").title()
        self.result_path = None

        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg="black")
        self.top.protocol("WM_DELETE_WINDOW", self.cancel)

        enhancer = ImageEnhance.Brightness(self.screenshot)
        self.dimmed_screenshot = enhancer.enhance(0.35)
        self.tk_dimmed = ImageTk.PhotoImage(self.dimmed_screenshot)

        self.canvas = tk.Canvas(self.top, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_dimmed)

        self.mag_size = 180
        self.mag_zoom = 4
        self.mag_canvas = tk.Canvas(
            self.top,
            width=self.mag_size,
            height=self.mag_size,
            highlightthickness=2,
            highlightbackground="#38bdf8",
            bg="black",
        )

        self.start_x = None
        self.start_y = None
        self.rect = None
        self.spotlight_item = None
        self.photo = None
        self.bright_tk = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.update_magnifier)
        self.top.bind("<Escape>", lambda _: self.cancel())

        self.canvas.create_text(
            24,
            24,
            text=f"Capturing {self.title} | Drag to save | ESC to cancel",
            anchor=tk.NW,
            fill="white",
            font=("Segoe UI", 16, "bold"),
        )
        self.canvas.create_text(
            24,
            52,
            text="Tip: zoom into the exact button, avoid shadows and background clutter.",
            anchor=tk.NW,
            fill="#bfdbfe",
            font=("Segoe UI", 10),
        )

    def cancel(self):
        if callable(self.on_cancel):
            self.on_cancel()
        self.top.destroy()

    def update_magnifier(self, event):
        x, y = event.x, event.y
        mag_x = x + 30 if x + self.mag_size + 60 < self.top.winfo_screenwidth() else x - self.mag_size - 30
        mag_y = y + 30 if y + self.mag_size + 60 < self.top.winfo_screenheight() else y - self.mag_size - 30
        self.mag_canvas.place(x=mag_x, y=mag_y)

        box_size = self.mag_size // self.mag_zoom
        left = max(0, x - box_size // 2)
        top = max(0, y - box_size // 2)
        right = min(self.screenshot.width, left + box_size)
        bottom = min(self.screenshot.height, top + box_size)

        part = self.screenshot.crop((left, top, right, bottom))
        part = part.resize((self.mag_size, self.mag_size), Image.Resampling.NEAREST)

        self.photo = ImageTk.PhotoImage(part)
        self.mag_canvas.delete("all")
        self.mag_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.mag_canvas.create_line(self.mag_size // 2, 0, self.mag_size // 2, self.mag_size, fill="red")
        self.mag_canvas.create_line(0, self.mag_size // 2, self.mag_size, self.mag_size // 2, fill="red")

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        if self.spotlight_item:
            self.canvas.delete(self.spotlight_item)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline="#38bdf8", width=2)

    def on_drag(self, event):
        x, y = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, x, y)

        left = min(self.start_x, x)
        top = min(self.start_y, y)
        right = max(self.start_x, x)
        bottom = max(self.start_y, y)

        if right - left > 2 and bottom - top > 2:
            bright_part = self.screenshot.crop((left, top, right, bottom))
            self.bright_tk = ImageTk.PhotoImage(bright_part)
            if self.spotlight_item:
                self.canvas.delete(self.spotlight_item)
            self.spotlight_item = self.canvas.create_image(left, top, anchor=tk.NW, image=self.bright_tk)
            self.canvas.tag_raise(self.rect)

        self.update_magnifier(event)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)

        if right - left < 3 or bottom - top < 3:
            return

        cropped = self.screenshot.crop((left, top, right, bottom))
        save_path = os.path.join(self.assets_dir, self.save_name)
        os.makedirs(self.assets_dir, exist_ok=True)
        cropped.save(save_path)

        self.result_path = save_path
        self.on_complete(self.result_path)
        self.top.destroy()


# ============================================================
# PHASE 5: COMBAT SIGNAL DETECTOR
# ============================================================

class CombatSignalDetector:
    """
    Fast pixel-perfect detection for combat signals in GPO BR.
    Uses HSV color region scanning — inspired by Deepwoken Fishing macro approach.
    All regions are configurable and user-picked via Settings UI.

    Detection signals:
    - green_hp_bar: enemy close enough to show HP bar above head
    - red_dmg_numbers: damage numbers flying up = confirmed hit
    - player_hp_bar: player's own HP bar (for FLEEING trigger)
    - incombat_timer: INCOMBAT indicator active at top-center
    - kill_icon: skull icon at top-right (kill confirmed)
    """

    HSV_RANGES = {
        "green_hp_bar": {
            "lower": None,
            "upper": None,
        },
        "red_dmg_numbers": {
            "lower1": None,
            "upper1": None,
            "lower2": None,
            "upper2": None,
        },
        "player_hp_bar": {
            "lower": None,
            "upper": None,
        },
        "incombat_timer": {
            "lower": None,
            "upper": None,
        },
        "kill_icon": {
            "lower": None,
            "upper": None,
        },
    }

    def __init__(self, config):
        self.config = config
        self._prev_green_frame_count = 0
        self._prev_red_frame_count = 0
        self._prev_incombat_frame_count = 0
        self._kill_count = 0
        self._init_hsv_ranges()

    def _init_hsv_ranges(self):
        """Initialize HSV ranges lazily (requires cv2)."""
        if not _CV2_AVAILABLE or np is None:
            return
        self.HSV_RANGES = {
            "green_hp_bar": {
                "lower": np.array([35, 60, 60], dtype=np.uint8),
                "upper": np.array([85, 255, 255], dtype=np.uint8),
            },
            "red_dmg_numbers": {
                "lower1": np.array([0, 100, 100], dtype=np.uint8),
                "upper1": np.array([10, 255, 255], dtype=np.uint8),
                "lower2": np.array([170, 100, 100], dtype=np.uint8),
                "upper2": np.array([180, 255, 255], dtype=np.uint8),
            },
            "player_hp_bar": {
                "lower": np.array([35, 60, 60], dtype=np.uint8),
                "upper": np.array([85, 255, 255], dtype=np.uint8),
            },
            "incombat_timer": {
                "lower": np.array([0, 0, 200], dtype=np.uint8),
                "upper": np.array([180, 40, 255], dtype=np.uint8),
            },
            "kill_icon": {
                "lower": np.array([0, 0, 180], dtype=np.uint8),
                "upper": np.array([180, 30, 255], dtype=np.uint8),
            },
        }

    def _get_region_bounds(self, region_name):
        """Get absolute pixel region from config (ratios -> pixels)."""
        from src.utils.config import get_combat_region
        return get_combat_region(self.config, region_name)

    def _get_threshold(self, region_name, default):
        """Get detection threshold for region."""
        from src.utils.config import get_combat_threshold
        return get_combat_threshold(self.config, region_name, default)

    def _capture_region(self, region):
        """Fast MSS capture of a specific pixel region. Returns RGB numpy array."""
        if not _MSS_AVAILABLE or np is None:
            return None
        if not region or len(region) != 4:
            return None
        try:
            with mss.mss() as sct:
                monitor = {
                    "left": int(region[0]),
                    "top": int(region[1]),
                    "width": int(region[2] - region[0]),
                    "height": int(region[3] - region[1]),
                }
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                if img.shape[2] == 4:
                    img = img[:, :, :3][:, :, ::-1]  # BGRA -> RGB
                return img
        except Exception:
            return None

    def _count_color_pixels(self, img, signal_name):
        """Count pixels matching a signal's color range. Returns (count, total, ratio)."""
        if img is None or img.size == 0 or not _CV2_AVAILABLE:
            return 0, 0, 0.0

        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        total = hsv.shape[0] * hsv.shape[1]

        ranges = self.HSV_RANGES.get(signal_name, {})
        if "lower" in ranges and "upper" in ranges:
            lower = ranges["lower"]
            upper = ranges["upper"]
            mask = cv2.inRange(hsv, lower, upper)
        elif "lower1" in ranges:
            lower1, upper1 = ranges["lower1"], ranges["upper1"]
            lower2, upper2 = ranges["lower2"], ranges["upper2"]
            mask1 = cv2.inRange(hsv, lower1, upper1)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            return 0, total, 0.0

        count = cv2.countNonZero(mask)
        return count, total, count / max(1, total)

    def scan_all_signals(self):
        """
        Scan all configured combat signals. Returns dict of signal -> bool.
        Call this once per combat tick (< 20ms total for all 5 regions).
        """
        results = {}

        # 1. GREEN HP BAR — primary enemy-close signal
        green_region = self._get_region_bounds("green_hp_bar")
        if green_region:
            img = self._capture_region(green_region)
            count, total, ratio = self._count_color_pixels(img, "green_hp_bar")
            threshold = self._get_threshold("green_hp_bar", 0.004)
            green_detected = ratio >= threshold
            if green_detected:
                self._prev_green_frame_count += 1
            else:
                self._prev_green_frame_count = max(0, self._prev_green_frame_count - 1)
            results["enemy_nearby"] = self._prev_green_frame_count >= 2
            results["_green_ratio"] = ratio
        else:
            results["enemy_nearby"] = False
            results["_green_ratio"] = 0.0

        # 2. RED DAMAGE NUMBERS — hit confirmation
        red_region = self._get_region_bounds("red_dmg_numbers")
        if red_region:
            img = self._capture_region(red_region)
            count, total, ratio = self._count_color_pixels(img, "red_dmg_numbers")
            threshold = self._get_threshold("red_dmg_numbers", 0.001)
            red_detected = ratio >= threshold
            if red_detected:
                self._prev_red_frame_count += 1
            else:
                self._prev_red_frame_count = max(0, self._prev_red_frame_count - 1)
            results["hit_confirmed"] = self._prev_red_frame_count >= 1
            results["_red_ratio"] = ratio
        else:
            results["hit_confirmed"] = False
            results["_red_ratio"] = 0.0

        # 3. PLAYER HP BAR — for FLEEING trigger
        player_region = self._get_region_bounds("player_hp_bar")
        if player_region:
            img = self._capture_region(player_region)
            count, total, ratio = self._count_color_pixels(img, "player_hp_bar")
            threshold = self._get_threshold("player_hp_bar", 0.005)
            results["player_hp_low"] = ratio < threshold
            results["_player_green_ratio"] = ratio
        else:
            results["player_hp_low"] = False
            results["_player_green_ratio"] = 0.0

        # 4. INCOMBAT TIMER — combat is active
        incombat_region = self._get_region_bounds("incombat_timer")
        if incombat_region:
            img = self._capture_region(incombat_region)
            count, total, ratio = self._count_color_pixels(img, "incombat_timer")
            threshold = self._get_threshold("incombat_timer", 0.002)
            incombat_detected = ratio >= threshold
            if incombat_detected:
                self._prev_incombat_frame_count += 1
            else:
                self._prev_incombat_frame_count = max(0, self._prev_incombat_frame_count - 1)
            results["in_combat"] = self._prev_incombat_frame_count >= 2
            results["_incombat_ratio"] = ratio
        else:
            results["in_combat"] = False
            results["_incombat_ratio"] = 0.0

        # 5. KILL ICON — kill confirmed
        kill_region = self._get_region_bounds("kill_icon")
        if kill_region:
            img = self._capture_region(kill_region)
            count, total, ratio = self._count_color_pixels(img, "kill_icon")
            threshold = self._get_threshold("kill_icon", 0.001)
            results["kill_confirmed"] = ratio >= threshold
            results["_kill_ratio"] = ratio
        else:
            results["kill_confirmed"] = False
            results["_kill_ratio"] = 0.0

        return results

    def get_debug_info(self):
        """Return current signal ratios for debugging/calibration."""
        return {
            "green_frame_count": self._prev_green_frame_count,
            "red_frame_count": self._prev_red_frame_count,
            "incombat_frame_count": self._prev_incombat_frame_count,
            "kill_count": self._kill_count,
        }

    def reset(self):
        """Clear frame counters — call on state transitions."""
        self._prev_green_frame_count = 0
        self._prev_red_frame_count = 0
        self._prev_incombat_frame_count = 0

    def increment_kill(self):
        self._kill_count += 1

    def get_kill_count(self):
        return self._kill_count


_combat_detector = None


def get_combat_detector(config):
    """Get or create combat signal detector singleton."""
    global _combat_detector
    if _combat_detector is None:
        _combat_detector = CombatSignalDetector(config)
    else:
        _combat_detector.config = config
    return _combat_detector

