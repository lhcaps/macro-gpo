"""
BridgerBackend.py — HTTP API server + GUI launcher for Bridger Fishing Macro

Provides:
  - BridgerHTTPServer on port 9760 with 3 endpoints:
      GET  /health   → { "status": "ok" }
      GET  /state    → full runtime state + config
      POST /command  → { "action": "...", "payload": "..." }
  - BridgerGUI: optional Tkinter window with status overlay
  - BridgerWindow: transparency overlay for status display

Launch:
    python BridgerBackend.py [--headless]
    python BridgerBackend.py          # starts GUI
    python BridgerBackend.py --headless  # HTTP only (used by Tauri frontend)
"""

import sys
import os
import json
import threading
import time
import logging
import base64
import math
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Detect frozen (PyInstaller) vs normal execution
if getattr(sys, 'frozen', False):
    _SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_SCRIPT_DIR, 'config.json')
LOG_DIR = os.path.join(_SCRIPT_DIR, 'logs')

# --- Logging setup ---
def _setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(os.path.join(LOG_DIR, 'summary.log'), encoding='utf-8')
    handler.setFormatter(logging.Formatter('[%(asctime)s] [PYTHON] %(message)s', '%H:%M:%S'))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

_setup_logging()
log = logging.getLogger(__name__)

# --- Default configuration ---
_DEFAULT_CONFIG = {
    "terms_accepted": False,
    "subscribed": False,
    "settings": {
        "use_bait": True,
        "bait_key": "2",
        "rod_key": "1",
        "cast_wait": 1.0,
        "between_casts": 1.5,
        "recovery_wait": 0.0,
        "verify_window": 0.7,
        "mg_blank_exit": 5,
        "skip_minigame": False,
        "detect_method": "numpy",
        "cv_threshold": 0.7,
        "match_threshold": 0.3,
        "rms_threshold": 0.015,
        "minigame_scan_delay": 0.05,
        "scan_delay_random": False,
        "scan_delay_min": 0.1,
        "scan_delay_max": 0.5,
        "monitor_index": 1,
        "cast_pos_custom": False,
        "cast_pos_x": 0.485,
        "cast_pos_y": 0.198,
        "numpy_white_thresh": 200,
        "blank_exit_stop": False,
        "blank_exit_stop_count": 10,
        "audio_device_index": -1,
        "webhook_enabled": False,
        "webhook_url": "",
        "webhook_user_id": "",
        "webhook_mode": "screenshot",
        "timeout_streak_webhook": 5,
        "timeout_streak_force_close": False,
        "webhook_notify_timeout": True,
        "webhook_notify_minigame": False,
        "webhook_notify_arrow_shard": True,
        "webhook_notify_reel": False,
        "webhook_ping_timeout": True,
        "webhook_ping_minigame": False,
        "webhook_ping_arrow_shard": True,
        "webhook_ping_reel": False,
        "repo_enabled": False,
        "walk_sequence": [],
        "walk_recordings": {},
        "walk_recording_active": "",
        "ocr_region": [0.474, 0.47, 0.531, 0.551],
        "ocr_tolerance": 40,
        "pixel_tolerance": 0,
        "pixel_anchor_tolerance": 0,
        "pixel_scan_delay": 0.03
    },
    "global_gui_settings": {
        "Always On Top": True,
        "Auto Minimize GUI": True,
        "Auto Focus Roblox": True,
        "Auto Maximize Roblox": True,
        "Show Status Overlay": True,
        "Show Audio Monitor": False
    },
    "hotkeys": {
        "start_stop": "f3",
        "exit": "f2",
        "select_region": "f1"
    }
}


def _deep_merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return _deep_merge(_DEFAULT_CONFIG, json.load(f))
    except Exception as e:
        log.warning(f"Failed to read config.json: {e}")
        return _DEFAULT_CONFIG.copy()


def _save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Failed to write config.json: {e}")


# --- Global application state ---
_state_lock = threading.Lock()
_app_config = _load_config()
_app_status = "Idle"
_app_audio = {}
_app_logs = []
_engine = None
_registered_hotkeys = {}
_start_pending = False


# --- Callback wrappers ---
def _cb_log(msg, level="info"):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    _app_logs.append({"ts": ts, "level": level, "msg": msg})
    if level == "err":
        log.error(msg)
    elif level == "warn":
        log.warning(msg)
    else:
        log.info(msg)


def _cb_status(text):
    global _app_status
    with _state_lock:
        _app_status = text


def _cb_score(corr, rms):
    with _state_lock:
        _app_audio = {"corr": round(corr, 4), "rms": round(rms, 6)}


def _cb_webhook(settings, event, data):
    if not settings.get("webhook_enabled") or not settings.get("webhook_url"):
        return
    if not settings.get(f"webhook_notify_{event}"):
        return

    url = settings["webhook_url"]
    user_id = settings.get("webhook_user_id", "")
    mode = settings.get("webhook_mode", "screenshot")

    ping_id = ""
    if settings.get(f"webhook_ping_{event}") and user_id:
        ping_id = f"<@{user_id}> "

    title_map = {
        "timeout": "Cast Timeout Streak Detected",
        "minigame": "Minigame Started",
        "arrow_shard": "Arrow Shard Detected!",
        "reel": "Reel Completed"
    }
    title = title_map.get(event, event.title())

    description_map = {
        "timeout": f"Cast timeout streak detected: {data.get('streak', 0)} consecutive timeouts",
        "minigame": "Minigame prompt detected",
        "arrow_shard": f"Arrow Shard detected! ({data.get('presses', 0)} presses)",
        "reel": "Fish reeled in successfully"
    }
    description = description_map.get(event, "")

    embed = {
        "content": ping_id,
        "embeds": [{
            "title": f"**Bridger** — {title}",
            "description": f"{ping_id}{description}",
            "color": 0,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        }]
    }

    if mode == "screenshot" and event in ("timeout", "arrow_shard"):
        import mss as _mss
        with _mss.mss() as sct:
            img = sct.grab(sct.monitors[1])
            png_bytes = _mss.tools.to_png(img.rgb, img.size)
            b64 = base64.b64encode(png_bytes).decode()
        embed["embeds"][0]["image"] = {"url": f"data:image/png;base64,{b64}"}

    try:
        import requests as _requests
        _requests.post(url, json=embed, timeout=10)
    except Exception as e:
        _cb_log(f"Webhook send failed: {e}", "err")


def _cb_force_close(cfg):
    _cb_log("Force close triggered — killing Roblox and stopping macro.", "err")
    try:
        os.system("taskkill /IM RobloxPlayerBeta.exe /F")
    except Exception as e:
        _cb_log(f"taskkill failed: {e}", "err")


# --- Engine initialisation ---
def _apply_config_to_engine(settings):
    if _engine is None:
        return
    _engine.cfg = settings
    _engine.monitor_index = settings.get("monitor_index", 1)
    _engine.audio_device_index = settings.get("audio_device_index", -1)
    _engine.ocr_region = settings.get("ocr_region", [0.474, 0.47, 0.531, 0.551])
    _engine.ocr_tolerance = settings.get("ocr_tolerance", 40)
    _engine.minigame_scan_delay = settings.get("minigame_scan_delay", 0.05)
    _engine.scan_delay_random = settings.get("scan_delay_random", False)
    _engine.scan_delay_min = settings.get("scan_delay_min", 0.1)
    _engine.scan_delay_max = settings.get("scan_delay_max", 0.5)
    _engine.detect_method = settings.get("detect_method", "numpy")
    _engine.pixel_tolerance = settings.get("pixel_tolerance", 0)
    _engine.pixel_anchor_tolerance = settings.get("pixel_anchor_tolerance", 0)
    _engine.pixel_scan_delay = settings.get("pixel_scan_delay", 0.03)


def _init_engine():
    global _engine
    try:
        from bridger import FishingEngine
        _engine = FishingEngine(
            log_fn=_cb_log,
            status_fn=_cb_status,
            score_fn=_cb_score,
            webhook_fn=_cb_webhook,
            force_close_fn=_cb_force_close,
        )
        _apply_config_to_engine(_app_config.get("settings", {}))
        _cb_log("FishingEngine initialised")
    except ImportError as e:
        _cb_log(f"Could not import FishingEngine from bridger.py: {e}", "err")


# --- Hotkey management ---
def _register_hotkeys():
    global _registered_hotkeys
    try:
        import keyboard
    except ImportError:
        _cb_log("keyboard module not available — hotkeys disabled", "warn")
        return

    hotkeys = _app_config.get("hotkeys", {})

    def make_callback(action):
        def cb():
            if action == "start_stop":
                if _engine and _engine.running:
                    _do_stop()
                else:
                    _do_start()
            elif action == "exit":
                _cb_log("Exit hotkey pressed — force exiting", "warn")
                os._exit(0)
            elif action == "select_region":
                _run_region_selector()
        return cb

    for name, key in hotkeys.items():
        try:
            keyboard.on_press_key(key, lambda e, cb=make_callback(name): cb())
            _registered_hotkeys[name] = key
        except Exception as e:
            _cb_log(f"Failed to bind hotkey {name}={key}: {e}", "err")

    _cb_log(f"Hotkeys registered: {_registered_hotkeys}")


def _update_hotkey(action, new_key):
    try:
        import keyboard
    except ImportError:
        return

    hotkeys = _app_config.get("hotkeys", {})
    old_key = hotkeys.get(action, "")
    try:
        keyboard.unbind(old_key)
        keyboard.on_press_key(new_key, lambda e: (
            _do_start() if action == "start_stop" else (
                os._exit(0) if action == "exit" else _run_region_selector()
            )
        ))
        hotkeys[action] = new_key
        _app_config["hotkeys"] = hotkeys
        _save_config(_app_config)
        _cb_log(f'Hotkey "{action}" rebound to "{new_key}"')
    except Exception as e:
        _cb_log(f'Failed to rebind hotkey {action} → {new_key}: {e}', "err")


# --- Focus Roblox ---
def _focus_roblox_window():
    gui_settings = _app_config.get("global_gui_settings", {})
    if not gui_settings.get("Auto Focus Roblox", True):
        return

    try:
        import ctypes
        from ctypes import wintypes
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible

        results = []
        def callback(hwnd, lparam):
            length = GetWindowTextLength(hwnd)
            if length == 0:
                return True
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buff, length + 1)
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if "roblox" in buff.value.lower() and IsWindowVisible(hwnd):
                results.append(hwnd)
            return True
        EnumWindows(EnumWindowsProc(callback), 0)
        if results:
            SetForegroundWindow(results[0])
    except Exception as e:
        _cb_log(f"Focus Roblox (non-fatal): {e}", "warn")


# --- Start / Stop ---
def _do_start():
    global _start_pending
    if _engine is None:
        _cb_log("start() called but engine not initialised", "err")
        return
    if _engine.running:
        return

    gui_settings = _app_config.get("global_gui_settings", {})
    if gui_settings.get("Auto Minimize GUI", True):
        pass  # Would minimize GUI window here

    _focus_roblox_window()
    _engine.start()
    _cb_log("[START] Macro running — switch to Roblox!", "ok")


def _do_stop():
    global _start_pending
    if _engine is None:
        return
    _engine.stop()
    _cb_log("[STOP] Macro stopped.", "info")


# --- Position Picker ---
class PositionPicker:
    """Full-screen transparent overlay — single click returns absolute (x, y)."""
    def __init__(self):
        try:
            import tkinter as tk
        except ImportError:
            raise RuntimeError("tkinter not available")

        self.root = tk.Tk()
        self.root.attributes('-topmost', True, '-alpha', 0.01)
        self.root.configure(background='black')
        self.root.configure(cursor='crosshair')
        self.root.bind('<Button-1>', self._on_click)
        self.root.bind('<Escape>', lambda e: self._cancel())
        self.result = None

    def _on_click(self, event):
        self.result = (event.x, event.y)
        self.root.quit()

    def _cancel(self):
        self.root.quit()

    def run(self):
        self.root.deiconify()
        self.root.mainloop()
        self.root.destroy()
        return self.result


def _run_position_picker():
    try:
        p = PositionPicker()
        result = p.run()
        if result:
            x, y = result
            mon = _engine._get_monitor()
            ratio_x = x / mon['width']
            ratio_y = y / mon['height']
            _app_config.setdefault('settings', {})['cast_pos_custom'] = True
            _app_config['settings']['cast_pos_x'] = ratio_x
            _app_config['settings']['cast_pos_y'] = ratio_y
            _save_config(_app_config)
            _apply_config_to_engine(_app_config['settings'])
            _cb_log(f"Cast position set: ({x}, {y}) -> ratio ({ratio_x:.4f}, {ratio_y:.4f})")
        else:
            _cb_log("Cast position pick cancelled")
    except Exception as e:
        _cb_log(f"PositionPicker failed: {e}", "err")


# --- OCR Region Selector ---
class OcrRegionSelector:
    """
    Hydra-style OCR region selector:
    screenshot background, pre-drawn box, drag corners to resize,
    drag inside to move, zoom lens follows cursor.
    Confirm: F1 or Enter. Cancel: Esc.
    Results are saved as normalised coordinates [x1, y1, x2, y2] (0-1 range).
    """
    def __init__(self):
        try:
            import tkinter as tk
        except ImportError:
            raise RuntimeError("tkinter not available")

        import mss
        import numpy as np

        # Capture full screen
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])
        self._bg = Image.frombytes('RGB', img.size, img.rgb)
        self._w, self._h = self._bg.size

        self.root = tk.Tk()
        self.root.title("Select OCR Region — F1/Enter: confirm  Esc: cancel")
        self.root.attributes('-topmost', True)
        canvas = tk.Canvas(self.root, width=self._w, height=self._h, cursor='cross')
        canvas.pack()

        bg_photo = self._pil_to_tk(self._bg)
        canvas.create_image(0, 0, anchor='nw', image=bg_photo)

        # Default region in centre
        x1 = int(self._w * 0.474)
        y1 = int(self._h * 0.47)
        x2 = int(self._w * 0.531)
        y2 = int(self._h * 0.551)

        self.selection = [x1, y1, x2, y2]
        self._drag_mode = None   # 'move', 'nw', 'ne', 'sw', 'se'
        self._start = (x1, y1)
        self._corner = 8

        self._rect = canvas.create_rectangle(x1, y1, x2, y2,
                                              outline='lime', width=2, dash=(4, 2))
        self._label = canvas.create_text((x1 + x2) // 2, y1 - 10,
                                          text=f"  {x1},{y1} → {x2},{y2}  ",
                                          fill='lime', font=('Consolas', 9))
        self._corners = [
            canvas.create_oval(x1 - self._corner, y1 - self._corner,
                               x1 + self._corner, y1 + self._corner,
                               fill='lime', outline='black'),
            canvas.create_oval(x2 - self._corner, y1 - self._corner,
                               x2 + self._corner, y1 + self._corner,
                               fill='lime', outline='black'),
            canvas.create_oval(x1 - self._corner, y2 - self._corner,
                               x1 + self._corner, y2 + self._corner,
                               fill='lime', outline='black'),
            canvas.create_oval(x2 - self._corner, y2 - self._corner,
                               x2 + self._corner, y2 + self._corner,
                               fill='lime', outline='black'),
        ]

        canvas.bind('<Button-1>', self._on_click)
        canvas.bind('<B1-Motion>', self._on_drag)
        canvas.bind('<ButtonRelease-1>', self._on_release)
        canvas.bind('<F1>', lambda e: self._confirm())
        canvas.bind('<Return>', lambda e: self._confirm())
        canvas.bind('<Escape>', lambda e: self._cancel())

        self._canvas = canvas

    def _pil_to_tk(self, pil_img):
        try:
            from PIL import ImageTk
        except ImportError:
            import tkinter as tk
            raise RuntimeError("PIL/Pillow ImageTk required")
        return ImageTk.PhotoImage(pil_img)

    def _update_rect(self):
        x1, y1, x2, y2 = self.selection
        self._canvas.coords(self._rect, x1, y1, x2, y2)
        self._canvas.coords(self._label, (x1 + x2) // 2, y1 - 10)
        self._canvas.itemconfig(self._label, text=f"  {x1},{y1} → {x2},{y2}  ")
        # Corner handles
        c = self._corner
        self._canvas.coords(self._corners[0], x1 - c, y1 - c, x1 + c, y1 + c)
        self._canvas.coords(self._corners[1], x2 - c, y1 - c, x2 + c, y1 + c)
        self._canvas.coords(self._corners[2], x1 - c, y2 - c, x1 + c, y2 + c)
        self._canvas.coords(self._corners[3], x2 - c, y2 - c, x2 + c, y2 + c)

    def _on_click(self, event):
        x, y = event.x, event.y
        x1, y1, x2, y2 = self.selection
        c = self._corner
        # Check corners first
        for name, cx, cy in [('nw', x1, y1), ('ne', x2, y1), ('sw', x1, y2), ('se', x2, y2)]:
            if abs(x - cx) <= c and abs(y - cy) <= c:
                self._drag_mode = name
                self._start = (x, y)
                return
        # Check inside
        if x1 <= x <= x2 and y1 <= y <= y2:
            self._drag_mode = 'move'
            self._start = (x, y)

    def _on_drag(self, event):
        if self._drag_mode is None:
            return
        x, y = event.x, event.y
        ox, oy = self._start
        dx, dy = x - ox, y - oy
        self._start = (x, y)
        x1, y1, x2, y2 = self.selection
        if self._drag_mode == 'move':
            self.selection = [x1 + dx, y1 + dy, x2 + dx, y2 + dy]
        elif self._drag_mode == 'nw':
            self.selection = [x1 + dx, y1 + dy, x2, y2]
        elif self._drag_mode == 'ne':
            self.selection = [x1, y1 + dy, x2 + dx, y2]
        elif self._drag_mode == 'sw':
            self.selection = [x1 + dx, y1, x2, y2 + dy]
        elif self._drag_mode == 'se':
            self.selection = [x1, y1, x2 + dx, y2 + dy]
        # Clamp
        x1, y1, x2, y2 = self.selection
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        self.selection = [max(0, x1), max(0, y1), min(self._w, x2), min(self._h, y2)]
        self._update_rect()

    def _on_release(self, event):
        self._drag_mode = None

    def _confirm(self):
        self.root.quit()

    def _cancel(self):
        self.selection = None
        self.root.quit()

    def run(self):
        self.root.deiconify()
        self.root.mainloop()
        self.root.destroy()
        if self.selection:
            x1, y1, x2, y2 = self.selection
            # Normalise to 0-1 range
            self.selection = [x1 / self._w, y1 / self._h, x2 / self._w, y2 / self._h]
        return self.selection


def _run_region_selector():
    try:
        s = OcrRegionSelector()
        result = s.run()
        if result:
            _app_config.setdefault('settings', {})['ocr_region'] = result
            _save_config(_app_config)
            _apply_config_to_engine(_app_config['settings'])
            _cb_log(f"OCR region updated: {result}")
        else:
            _cb_log("OCR region selection cancelled")
    except Exception as e:
        _cb_log(f"OcrRegionSelector failed: {e}", "err")


# --- Auto-subscribe ---
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@repetitives1?sub_confirmation=1"


def _auto_subscribe():
    try:
        import webbrowser
        import time
        webbrowser.open(YOUTUBE_CHANNEL_URL)
        time.sleep(2)
    except Exception as e:
        _cb_log(f"Auto-subscribe error: {e}", "err")


# --- Command handler ---
def _handle_command(action, payload=None):
    _cb_log(f"Command received: action={action}")

    if action == "start":
        _do_start()
        return {"status": "ok"}
    elif action == "stop":
        _do_stop()
        return {"status": "ok"}
    elif action == "quit_app":
        _cb_log("quit_app — initiating shutdown")
        os._exit(0)
    elif action == "set_setting":
        key = payload.get("key") if payload else None
        value = payload.get("value") if payload else None
        if key and value is not None:
            _app_config.setdefault('settings', {})[key] = value
            _save_config(_app_config)
            _apply_config_to_engine(_app_config['settings'])
        return {"status": "ok"}
    elif action == "set_settings":
        settings = payload or {}
        _app_config['settings'] = _deep_merge(_app_config.get('settings', {}), settings)
        _save_config(_app_config)
        _apply_config_to_engine(_app_config['settings'])
        return {"status": "ok"}
    elif action == "set_global_gui_setting":
        key = payload.get("key") if payload else None
        value = payload.get("value") if payload else None
        if key and value is not None:
            _app_config.setdefault('global_gui_settings', {})[key] = value
            _save_config(_app_config)
        return {"status": "ok"}
    elif action == "save_config":
        _save_config(_app_config)
        return {"status": "ok"}
    elif action == "rebind_hotkey":
        hotkey = payload.get("action") if payload else None
        new_key = payload.get("key") if payload else None
        if hotkey and new_key:
            _update_hotkey(hotkey, new_key)
        return {"status": "ok"}
    elif action == "select_region":
        threading.Thread(target=_run_region_selector, daemon=True).start()
        return {"status": "ok"}
    elif action == "pick_cast_position":
        threading.Thread(target=_run_position_picker, daemon=True).start()
        return {"status": "ok"}
    elif action == "get_devices":
        if _engine:
            return {"devices": _engine.get_loopback_devices()}
        return {"devices": []}
    elif action == "load_cv_templates":
        if _engine:
            _engine.load_cv_templates()
        return {"status": "ok"}
    elif action == "test_detection":
        if _engine:
            letter, score = _engine._detect_letter(_engine._capture(_engine.ocr_region),
                                                    method=_engine.detect_method)
            thr = _engine.cfg.get('cv_threshold', 0.7)
            return {"letter": letter, "score": score, "threshold": thr}
        return {"error": "Engine not running"}
    elif action == "save_walk_recording":
        name = payload.get("name") if payload else None
        steps = payload.get("steps") if payload else []
        if not name:
            return {"error": "Name cannot be empty"}
        _app_config.setdefault('settings', {}).setdefault('walk_recordings', {})[name] = steps
        if name not in _app_config['settings'].get('walk_sequence', []):
            _app_config['settings'].setdefault('walk_sequence', []).append(name)
        _save_config(_app_config)
        return {"status": "ok"}
    elif action == "load_walk_recording":
        name = payload.get("name") if payload else None
        recordings = _app_config.get('settings', {}).get('walk_recordings', {})
        recording = recordings.get(name)
        if not recording:
            return {"error": "Recording not found"}
        return {"steps": recording}
    elif action == "delete_walk_recording":
        name = payload.get("name") if payload else None
        if name:
            recordings = _app_config.get('settings', {}).get('walk_recordings', {})
            recordings.pop(name, None)
            seq = _app_config['settings'].get('walk_sequence', [])
            if name in seq:
                seq.remove(name)
            _save_config(_app_config)
        return {"status": "ok"}
    elif action == "rename_walk_recording":
        old_name = payload.get("old_name") if payload else None
        new_name = payload.get("new_name") if payload else None
        if not new_name:
            return {"error": "New name cannot be empty"}
        recordings = _app_config.get('settings', {}).get('walk_recordings', {})
        if old_name in recordings:
            recordings[new_name] = recordings.pop(old_name)
            seq = _app_config['settings'].get('walk_sequence', [])
            if old_name in seq:
                seq[seq.index(old_name)] = new_name
            _save_config(_app_config)
        return {"status": "ok"}
    elif action == "accept_tos":
        _app_config['terms_accepted'] = True
        _save_config(_app_config)
        _cb_log("TOS accepted")
        return {"status": "ok"}
    elif action == "auto_subscribe":
        if not _app_config.get('subscribed', False):
            _auto_subscribe()
            _app_config['subscribed'] = True
            _save_config(_app_config)
        else:
            return {"status": "already_subscribed"}
        return {"status": "ok"}
    elif action == "reset_config":
        _app_config = _DEFAULT_CONFIG.copy()
        try:
            _save_config(_app_config)
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "ok"}
    else:
        return {"error": f"Unknown command: {action}"}


# --- HTTP Server ---
class ThreadingMixIn:
    daemon_threads = True
    blocking_mode = False


class BridgerHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        pass


class BridgerHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, format, *args):
        pass

    def send_json(self, data, code=200):
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/health':
            self.send_json({"status": "ok"})
            return

        if parsed.path == '/state':
            with _state_lock:
                audio = dict(_app_audio)
            monitors = []
            try:
                import mss
                with mss.mss() as sct:
                    monitors = [{"index": i, **m} for i, m in enumerate(sct.monitors)]
            except Exception:
                pass

            config = dict(_app_config)
            if _engine:
                config['_engine_state'] = {
                    "running": _engine.running,
                    "cast_num": _engine.cast_num,
                    "stat_minigame": _engine.stat_minigame,
                    "stat_no_minigame": _engine.stat_no_minigame,
                    "stat_timeouts": _engine.stat_timeouts,
                    "stat_chest": _engine.stat_chest,
                    "stat_mare": _engine.stat_mare,
                    "stat_arrow_shard": _engine.stat_arrow_shard,
                }
            config['_hotkeys'] = _app_config.get('hotkeys', {})
            config['_status'] = _app_status
            config['_logs'] = _app_logs[-50:]

            state = {
                "running": _engine.running if _engine else False,
                "status": _app_status,
                "audio": audio,
                "monitors": monitors,
                "config": config,
                "logs": _app_logs[-50:],
            }
            self.send_json(state)
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/command':
            self.send_json({"error": "Not found"}, 404)
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')

        try:
            data = json.loads(body)
        except Exception:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        result = _handle_command(data.get("action", ""), data.get("payload"))
        self.send_json(result)


# --- Optional Tkinter Status Overlay ---
class BridgerStatusOverlay:
    """Transparent overlay window showing macro status and audio levels."""
    def __init__(self, width=360, height=200):
        try:
            import tkinter as tk
        except ImportError:
            raise

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True,
                              '-alpha', 0.85,
                              '-transparentcolor', 'black')
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}+{sw - width - 20}+{sh - height - 80}")
        self.root.configure(background='black')

        self._status_var = tk.StringVar(value="Idle")
        self._corr_var = tk.StringVar(value="--")
        self._rms_var = tk.StringVar(value="--")
        self._cast_var = tk.StringVar(value="Cast: 0")
        self._label = tk.Label(self.root, textvariable=self._status_var,
                                fg='lime', bg='black', font=('Consolas', 14, 'bold'),
                                pady=4)
        self._label.pack()
        self._audio_frame = tk.Frame(self.root, bg='black')
        self._audio_frame.pack(pady=4)
        tk.Label(self._audio_frame, text="corr:", fg='#aaa', bg='black',
                  font=('Consolas', 9)).grid(row=0, column=0, sticky='w')
        tk.Label(self._audio_frame, textvariable=self._corr_var, fg='white', bg='black',
                  font=('Consolas', 9, 'bold')).grid(row=0, column=1, sticky='w', padx=(0, 12))
        tk.Label(self._audio_frame, text="rms:", fg='#aaa', bg='black',
                  font=('Consolas', 9)).grid(row=0, column=2, sticky='w')
        tk.Label(self._audio_frame, textvariable=self._rms_var, fg='white', bg='black',
                  font=('Consolas', 9, 'bold')).grid(row=0, column=3, sticky='w')
        self._cast_label = tk.Label(self.root, textvariable=self._cast_var,
                                    fg='#aaa', bg='black', font=('Consolas', 9))
        self._cast_label.pack()

        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)

    def _update_loop(self):
        import time
        while self._running:
            try:
                self.root.after(0, self._refresh_ui)
            except Exception:
                pass
            time.sleep(0.1)

    def _refresh_ui(self):
        try:
            with _state_lock:
                status = _app_status
                audio = dict(_app_audio)
            self._status_var.set(status)
            self._corr_var.set(str(audio.get('corr', '--')))
            self._rms_var.set(str(audio.get('rms', '--')))
            if _engine:
                self._cast_var.set(f"Cast: {_engine.cast_num}  Minigame: {_engine.stat_minigame}")
        except Exception:
            pass

    def start(self):
        self._thread.start()
        self.root.mainloop()

    def stop(self):
        self._running = False
        try:
            self.root.quit()
        except Exception:
            pass


# --- Main ---
def main():
    global _app_config
    _app_config = _load_config()

    if not _app_config.get('terms_accepted', False):
        _cb_log("Terms of service not accepted yet")

    _init_engine()
    _register_hotkeys()

    server = BridgerHTTPServer(('127.0.0.1', 9760), BridgerHandler)
    _cb_log("Listening on http://127.0.0.1:9760")

    if '--headless' not in sys.argv:
        _cb_log("Starting optional status overlay...")
        # Start overlay in background thread, keep HTTP running
        def run_overlay():
            try:
                overlay = BridgerStatusOverlay()
                overlay.start()
            except Exception as e:
                _cb_log(f"Overlay error (non-fatal): {e}", "warn")
        threading.Thread(target=run_overlay, daemon=True).start()

    server.serve_forever()


if __name__ == '__main__':
    main()
