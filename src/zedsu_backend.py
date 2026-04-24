"""
ZedsuBackend — Tier 2 HTTP API server wrapping ZedsuCore.

Per D-09c: fixed port 9761, no auth (localhost only).
Per D-09g: 3 IPC commands — send_action, get_state, restart_backend.
Per D-09b: hierarchical JSON state snapshot from /state.

Launches ZedsuCore in a daemon thread, implements CoreCallbacks,
serves HTTP on port 9761 for ZedsuFrontend (Tier 3).
"""
import json
import logging
import os
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# D-11.5a-02: emergency_stop releases all held game keys
import pydirectinput
from typing import Optional
from urllib.parse import urlparse

# Path resolution (PyInstaller compatible)
if getattr(sys, 'frozen', False):
    _SCRIPT_DIR = os.path.dirname(sys.executable)
    _PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
CONFIG_PATH = os.path.join(_PROJECT_ROOT, 'config.json')
LOG_DIR = os.path.join(_SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

PORT = 9761  # per D-09c-01
HOST = '127.0.0.1'  # localhost only per D-09c-02


# ============================================================================
# Logging setup (Bridger pattern)
# ============================================================================

_backend_handler = logging.FileHandler(
    os.path.join(LOG_DIR, 'backend.log'), encoding='utf-8'
)
_backend_handler.setFormatter(
    logging.Formatter('[%(asctime)s] [BACKEND] %(message)s', '%H:%M:%S')
)
logging.getLogger().addHandler(_backend_handler)
logging.getLogger().setLevel(logging.INFO)
_backend_log = logging.getLogger('zedsu_backend')


# ============================================================================
# Global state (thread-safe)
# ============================================================================

_state_lock = threading.Lock()
_app_status = "Idle"
_app_status_color = "#475569"
_app_logs = []  # last 100 entries
_app_config = {}
_core_instance = None
_restart_count = 0
_start_time = time.time()

# D-11.5a-02: Safety helper — releases ALL held game keys
# Called by emergency_stop to ensure no key is stuck after hard stop.
def _release_all_game_keys():
    _backend_log.warning("[EMERGENCY] Releasing all game keys...")
    keys_to_release = {"w", "a", "s", "d", "shift", "space", "e", "r", "q", "f"}
    try:
        config_keys = (_app_config.get("keys") or {}).values()
        keys_to_release.update(str(k).lower() for k in config_keys)
    except Exception:
        pass
    released = []
    for key in keys_to_release:
        try:
            pydirectinput.keyUp(key)
            released.append(key)
        except Exception:
            pass
    if released:
        _backend_log.warning(f"[EMERGENCY] Released keys: {released}")

# Phase 11: YOLO training capture state
_yolo_capture_active = False
_yolo_capture_class = "enemy_player"
_yolo_capture_count = 0
_yolo_capture_start_time = 0.0
_yolo_capture_thread = None

# Phase 11: YOLO model quality validation state
_yolo_quality_score = None
_yolo_quality_checked = False
_yolo_quality_warning = False
_yolo_quality_error = None

# YOLO class names for dataset stats
try:
    from src.core.vision_yolo import YOLODetector
except ImportError:
    class _DummyYOLODetector:
        CLASS_NAMES = {}
    YOLODetector = _DummyYOLODetector


# ============================================================================
# BackendCallbacks — implements CoreCallbacks for ZedsuCore
# ============================================================================

class BackendCallbacks:
    """
    Implements CoreCallbacks — ZedsuCore calls these.
    Backend owns config, logging, and Discord integration.
    """

    def log(self, msg: str, level: str = "info") -> None:
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        with _state_lock:
            _app_logs.append({"ts": ts, "level": level, "msg": msg})
            if len(_app_logs) > 100:
                _app_logs[:] = _app_logs[-100:]
        if level == "error":
            _backend_log.error(msg)
        elif level == "warn":
            _backend_log.warning(msg)
        else:
            _backend_log.info(msg)

    def status(self, text: str, color: str = "#475569") -> None:
        global _app_status, _app_status_color
        with _state_lock:
            _app_status = text
            _app_status_color = color

    def discord(self, message: str, screenshot_path: Optional[str] = None, event: str = "info") -> None:
        """Send Discord notification via send_discord()."""
        webhook_url = _app_config.get("discord_webhook", "")
        if not webhook_url:
            return
        try:
            from src.utils.discord import send_discord
            status_code = send_discord(webhook_url, message, screenshot_path)
            if status_code:
                self.log(f"Discord notification sent ({status_code})")
            else:
                self.log(f"Discord notification failed (no status)", "warn")
        except Exception as e:
            self.log(f"Discord send failed: {e}", "error")

    def config(self) -> dict:
        """Return current config dict from memory."""
        return dict(_app_config)

    # --- Additional callbacks used by _ZedsuBotEngine ---

    def is_running(self) -> bool:
        global _core_instance
        return _core_instance is not None and _core_instance._running

    def sleep(self, seconds: float) -> bool:
        """Sleep with interrupt check."""
        end_time = time.time() + max(0, seconds)
        while time.time() < end_time:
            if not self.is_running():
                return False
            time.sleep(0.1)
        return True

    def log_error(self, msg: str) -> None:
        self.log(msg, "error")

    def invalidate_runtime_caches(self, clear_region: bool = False) -> None:
        global _core_instance
        if _core_instance and hasattr(_core_instance, '_engine'):
            _core_instance._engine.invalidate_region_cache()

    def get_search_region(self) -> Optional[dict]:
        """Get current window region for screen capture."""
        from src.utils.config import get_asset_capture_context
        try:
            return get_asset_capture_context()
        except Exception:
            return None

    def is_visible(self, image_key: str, confidence: Optional[float] = None,
                  search_context: Optional[dict] = None) -> bool:
        from src.core.vision import is_image_visible
        try:
            return is_image_visible(image_key, _app_config, confidence, search_context)
        except Exception:
            return False

    def safe_find_and_click(self, image_key: str, confidence: Optional[float] = None) -> bool:
        from src.core.vision import find_and_click
        try:
            # D-11.5f-01: pass is_running_check and log_func in correct order
            return find_and_click(image_key, _app_config, self.is_running, self.log, confidence=confidence)
        except Exception:
            return False

    def build_search_context(self) -> dict:
        from src.core.vision import capture_search_context
        try:
            return capture_search_context()
        except Exception:
            return {}

    def resolve_coordinate(self, key: str) -> Optional[tuple]:
        from src.utils.config import resolve_coordinate as _rc
        try:
            return _rc(_app_config, key)
        except Exception:
            return None

    def resolve_outcome_area(self) -> Optional[tuple]:
        from src.utils.config import resolve_outcome_area as _roa
        try:
            return _roa(_app_config)
        except Exception:
            return None

    def locate_image(self, image_key: str, confidence: Optional[float] = None) -> Optional[tuple]:
        from src.core.vision import locate_image
        try:
            return locate_image(image_key, _app_config, confidence)
        except Exception:
            return None

    def click_saved_coordinate(self, key: str, label: str, clicks: int = 1) -> bool:
        # D-11.5g-01: import locate_image from src.core.vision
        from src.core.vision import locate_image
        try:
            result = locate_image(key, _app_config, None)
            if result:
                from src.core.controller import human_click
                cx = result[0] + result[2] // 2
                cy = result[1] + result[3] // 2
                return human_click(cx, cy, self.is_running, offset=2)
        except Exception:
            pass
        return False

    def get_combat_detector(self):
        from src.core.vision import get_combat_detector
        return get_combat_detector(_app_config)

    def get_yolo_detector(self):
        from src.core.vision import _get_yolo_detector
        return _get_yolo_detector()

    def get_combat_state(self) -> str:
        global _core_instance
        if _core_instance and hasattr(_core_instance, '_engine'):
            return _core_instance._engine.get_combat_state()
        return "IDLE"

    def get_combat_debug_info(self) -> dict:
        global _core_instance
        if _core_instance and hasattr(_core_instance, '_engine'):
            return _core_instance._engine.get_combat_debug_info()
        return {}

    def reset_combat(self) -> None:
        global _core_instance
        if _core_instance and hasattr(_core_instance, '_engine'):
            _core_instance._engine.reset_combat()

    def on_match_detected(self, reason: str = "") -> None:
        global _core_instance
        if _core_instance and hasattr(_core_instance, '_engine'):
            eng = _core_instance._engine
            eng._match_count += 1
            eng.match_start_time = time.time()
            eng.match_active = True

    def invalidate_region_cache(self) -> None:
        global _core_instance
        if _core_instance and hasattr(_core_instance, '_engine'):
            _core_instance._engine.invalidate_region_cache()


# ============================================================================
# Phase 11: YOLO Training — helper functions
# ============================================================================

def _get_yolo_dataset_stats() -> dict:
    """Count images per class in dataset_yolo/ folder."""
    dataset_root = os.path.join(os.getcwd(), "dataset_yolo")
    class_counts = {}
    if os.path.isdir(dataset_root):
        for class_name in YOLODetector.CLASS_NAMES.values():
            class_dir = os.path.join(dataset_root, class_name)
            if os.path.isdir(class_dir):
                class_counts[class_name] = len([
                    f for f in os.listdir(class_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                ])
            else:
                class_counts[class_name] = 0
    return class_counts


def _get_yolo_model_info() -> dict:
    """Get YOLO model availability and metadata."""
    try:
        det = YOLODetector()
        det._load_model()  # force load attempt
        return {
            "available": det._model_loaded,
            "path": det._get_default_model_path(),
            "error": det._model_load_error,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def _validate_yolo_model() -> dict:
    """
    Run model quality validation on startup.
    D-11d-01: F1 < 60% triggers quality_warning = True.
    Results cached in _yolo_quality_score, _yolo_quality_warning.
    """
    global _yolo_quality_score, _yolo_quality_checked, _yolo_quality_warning, _yolo_quality_error

    if _yolo_quality_checked:
        return {
            "score": _yolo_quality_score,
            "warning": _yolo_quality_warning,
            "error": _yolo_quality_error,
        }

    _yolo_quality_checked = True

    try:
        from src.core.vision_yolo import validate_model_on_dataset
        result = validate_model_on_dataset()

        if "error" in result:
            _yolo_quality_error = result["error"]
            _yolo_quality_score = None
            _yolo_quality_warning = False
            _backend_log.warning(f"YOLO quality validation: {result['error']}")
        else:
            score = result.get("f1", 0.0)
            _yolo_quality_score = score
            _yolo_quality_warning = score < 0.60
            _yolo_quality_error = None

            if _yolo_quality_warning:
                _backend_log.warning(
                    f"YOLO model quality low: F1={score:.1%} (threshold: 60%). "
                    f"Consider retraining with more data."
                )
                print(f"[WARNING] YOLO model quality low: F1={score:.1%} — consider retraining")
            else:
                _backend_log.info(f"YOLO model quality: F1={score:.1%}")

    except Exception as e:
        _yolo_quality_error = str(e)
        _yolo_quality_score = None
        _yolo_quality_warning = False
        _backend_log.error(f"YOLO quality validation failed: {e}")

    return {
        "score": _yolo_quality_score,
        "warning": _yolo_quality_warning,
        "error": _yolo_quality_error,
    }


def _yolo_capture_loop():
    """Background thread: captures 1 frame/second to dataset_yolo/{class}/."""
    global _yolo_capture_active, _yolo_capture_count, _yolo_capture_class

    import time as _capture_time
    dataset_dir = os.path.join(os.getcwd(), "dataset_yolo", _yolo_capture_class)
    os.makedirs(dataset_dir, exist_ok=True)

    while _yolo_capture_active:
        try:
            region = None
            try:
                from src.utils.config import get_asset_capture_context
                region = get_asset_capture_context()
            except Exception:
                pass

            if region:
                import mss
                import numpy as np
                with mss.mss() as sct:
                    screenshot = sct.grab(region)
                    img = np.array(screenshot)
                    img_bgr = img[:, :, :3][:, :, ::-1]
                    import cv2
                    filename = f"{_yolo_capture_class}_{int(_capture_time.time()*1000)}.png"
                    filepath = os.path.join(dataset_dir, filename)
                    cv2.imwrite(filepath, img_bgr)
                    _yolo_capture_count += 1
                    _backend_log.info(f"YOLO capture: {filename} ({_yolo_capture_count} total)")
        except Exception as e:
            _backend_log.error(f"YOLO capture error: {e}")

        for _ in range(10):
            if not _yolo_capture_active:
                break
            _capture_time.sleep(0.1)


# ============================================================================
# ZedsuCore launch with restart logic
# ============================================================================

def _launch_core() -> None:
    """Launch or restart ZedsuCore in a daemon thread."""
    global _core_instance, _restart_count

    if _core_instance is not None:
        _core_instance.stop()
        _core_instance = None

    try:
        from src.zedsu_core import ZedsuCore
        callbacks = BackendCallbacks()
        _core_instance = ZedsuCore(callbacks=callbacks)
        _core_instance.start()
        _backend_log.info("ZedsuCore started")
        _restart_count = 0
    except Exception as e:
        _backend_log.error(f"Failed to start ZedsuCore: {e}")
        _restart_count += 1
        if _restart_count >= 3:
            _backend_log.critical("Max restart attempts reached — giving up")
            raise


# ============================================================================
# HTTP Handler (3 endpoints per D-09g)
# ============================================================================

class ZedsuHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _set_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_json(self, data, code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._set_cors()
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def log_message(self, fmt, *args):
        pass  # Silence default stderr logging

    def do_GET(self):
        global _yolo_quality_score, _yolo_quality_warning, _yolo_quality_error, _app_config

        parsed = urlparse(self.path)

        if parsed.path == '/health':
            # per D-09g-01: health check
            with _state_lock:
                alive = _core_instance is not None and _core_instance._running
            self._send_json({"status": "ok" if alive else "down"})
            return

        if parsed.path == '/state':
            # per D-09b-01: hierarchical JSON state snapshot
            with _state_lock:
                status = _app_status
                status_color = _app_status_color
                logs = list(_app_logs[-20:])

            core_state = {}
            if _core_instance is not None and hasattr(_core_instance, 'get_state'):
                try:
                    core_state = _core_instance.get_state()
                except Exception:
                    core_state = {}

            # Strip secrets before sending to frontend
            config_for_frontend = dict(_app_config)
            config_for_frontend.pop("discord_webhook", None)
            config_for_frontend.pop("discord_webhook_url", None)

            # Run quality validation if not yet checked (Phase 11)
            if not _yolo_quality_checked:
                _validate_yolo_model()

            # Get dataset readiness
            try:
                from src.core.vision_yolo import get_dataset_readiness
                dataset_readiness = get_dataset_readiness()
            except Exception:
                dataset_readiness = {}

            yolo_model_info = _get_yolo_model_info()
            dataset_stats = _get_yolo_dataset_stats()

            state = {
                "running": _core_instance is not None and _core_instance._running,
                "status": status,
                "status_color": status_color,
                "logs": logs,
                "combat": core_state.get("combat", {}),
                "vision": core_state.get("vision", {}),
                "stats": {
                    "combat_state": core_state.get("combat_state", "IDLE"),
                    "kills": core_state.get("kills", 0),
                    "match_count": core_state.get("match_count", 0),
                },
                "config": config_for_frontend,
                "yolo_model": {
                    "available": yolo_model_info["available"],
                    "model_path": yolo_model_info["path"],
                    "model_error": yolo_model_info.get("error"),
                    "quality_score": _yolo_quality_score,
                    "quality_warning": _yolo_quality_warning,
                    "quality_error": _yolo_quality_error,
                    "capturing": _yolo_capture_active,
                    "capture_class": _yolo_capture_class,
                    "capture_count": _yolo_capture_count,
                    "dataset_stats": dataset_stats,
                    "dataset_readiness": dataset_readiness,
                },
            }
            self._send_json(state)
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        global _app_config, _yolo_capture_active, _yolo_capture_class, _yolo_capture_count, _yolo_capture_start_time, _yolo_capture_thread, _yolo_quality_score, _yolo_quality_checked, _yolo_quality_warning, _yolo_quality_error
        parsed = urlparse(self.path)
        if parsed.path != '/command':
            self._send_json({"error": "Not found"}, 404)
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        try:
            data = json.loads(body)
        except Exception:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        action = data.get("action", "")
        payload = data.get("payload")

        # per D-09g-01: send_action + restart_backend
        try:
            # Phase 11: declare globals for all YOLO capture/model globals
            global _yolo_capture_active, _yolo_capture_class, _yolo_capture_count
            global _yolo_capture_start_time, _yolo_capture_thread
            global _yolo_quality_score, _yolo_quality_checked, _yolo_quality_warning, _yolo_quality_error

            if action == "start":
                _launch_core()
                self._send_json({"status": "ok"})

            elif action == "stop":
                if _core_instance:
                    _core_instance.stop()
                self._send_json({"status": "ok"})

            elif action == "restart_backend":
                _launch_core()
                self._send_json({"status": "ok"})

            elif action == "reload_config":
                global _app_config
                from src.utils.config import load_config
                _app_config = load_config()
                self._send_json({"status": "ok", "config": dict(_app_config)})

            elif action == "save_config":
                from src.utils.config import save_config
                save_config(_app_config)
                self._send_json({"status": "ok"})

            elif action == "pause":
                if _core_instance:
                    _core_instance.pause()
                self._send_json({"status": "ok"})

            elif action == "resume":
                if _core_instance:
                    _core_instance.resume()
                self._send_json({"status": "ok"})

            elif action == "toggle":
                # D-11.5a-03: idempotent toggle — stop if running, start if idle
                if _core_instance is not None and _core_instance._running:
                    _core_instance.stop()
                    _backend_log.info("[COMMAND] toggle → stopped")
                else:
                    _launch_core()
                    _backend_log.info("[COMMAND] toggle → started")
                self._send_json({"status": "ok"})

            elif action == "emergency_stop":
                # D-11.5a-02: hard stop — release keys + stop core + mark IDLE
                global _app_status, _app_status_color
                _release_all_game_keys()
                if _core_instance is not None:
                    _core_instance.stop()
                with _state_lock:
                    _app_status = "IDLE"
                    _app_status_color = "#475569"
                _backend_log.warning("[EMERGENCY] emergency_stop triggered")
                self._send_json({"status": "ok"})

            elif action == "update_config":
                # D-11.5a-04: partial config update via deep merge
                from src.utils.config import _deep_merge
                if payload is None:
                    self._send_json({"status": "error", "message": "payload required"}, 400)
                    return
                _app_config = _deep_merge(_app_config, payload)
                self._send_json({"status": "ok"})

            # Phase 11: YOLO capture commands
            elif action == "yolo_capture_start":
                # D-11a-02: Toggle capture mode — start continuous 1fps capture
                payload_data = data.get("payload", {})
                target_class = payload_data.get("class_name", _yolo_capture_class)
                if target_class not in YOLODetector.CLASS_NAMES.values():
                    self._send_json({"status": "error", "message": f"Unknown class: {target_class}"}, 400)
                    return
                _yolo_capture_active = True
                _yolo_capture_class = target_class
                _yolo_capture_count = 0
                _yolo_capture_start_time = time.time()
                _yolo_capture_thread = threading.Thread(target=_yolo_capture_loop, daemon=True, name="YoloCapture")
                _yolo_capture_thread.start()
                _backend_log.info(f"YOLO capture started: class={target_class}")
                self._send_json({"status": "ok", "capturing": True, "class": target_class})

            elif action == "yolo_capture_stop":
                was_active = _yolo_capture_active
                _yolo_capture_active = False
                if was_active:
                    elapsed = time.time() - _yolo_capture_start_time
                    _backend_log.info(f"YOLO capture stopped: {_yolo_capture_count} images in {elapsed:.1f}s")
                self._send_json({"status": "ok", "capturing": False, "total_captured": _yolo_capture_count})

            # Phase 11: YOLO model management
            elif action == "yolo_model_list":
                import glob as _glob
                models_dir = os.path.join(os.getcwd(), "assets", "models")
                os.makedirs(models_dir, exist_ok=True)
                active = os.path.join(models_dir, "yolo_gpo.onnx")
                backups = sorted(_glob.glob(os.path.join(models_dir, "yolo_gpo_backup_*.onnx")), reverse=True)
                models = []
                for backup in backups:
                    name = os.path.basename(backup)
                    ts = name.replace("yolo_gpo_backup_", "").replace(".onnx", "")
                    size_mb = os.path.getsize(backup) / (1024 * 1024)
                    models.append({
                        "name": name,
                        "path": backup,
                        "timestamp": ts,
                        "size_mb": round(size_mb, 2),
                        "active": False,
                        "type": "backup",
                    })
                if os.path.exists(active):
                    models.insert(0, {
                        "name": "yolo_gpo.onnx",
                        "path": active,
                        "timestamp": None,
                        "size_mb": round(os.path.getsize(active) / (1024 * 1024), 2),
                        "active": True,
                        "type": "active",
                    })
                self._send_json({"status": "ok", "models": models})

            elif action == "yolo_activate_model":
                import glob as _glob
                payload_data = data.get("payload", {})
                model_name = payload_data.get("model_name", "")
                if not model_name:
                    self._send_json({"status": "error", "message": "model_name required"}, 400)
                    return
                # Path traversal defense: reject paths with directory separators or parent refs
                if ".." in model_name or "/" in model_name or "\\" in model_name:
                    self._send_json({"status": "error", "message": f"Invalid model name: {model_name}"}, 400)
                    return
                models_dir = os.path.join(os.getcwd(), "assets", "models")
                source = os.path.join(models_dir, model_name)
                active = os.path.join(models_dir, "yolo_gpo.onnx")
                if not os.path.exists(source):
                    self._send_json({"status": "error", "message": f"Model not found: {model_name}"}, 404)
                    return
                if model_name == "yolo_gpo.onnx":
                    self._send_json({"status": "ok", "message": "Already active", "model": model_name})
                    return
                if os.path.exists(active):
                    rollback_backup = os.path.join(models_dir, f"yolo_gpo_rollback_{time.strftime('%Y%m%d_%H%M')}.onnx")
                    shutil.copy2(active, rollback_backup)
                    _backend_log.info(f"Rolled back current model to: {rollback_backup}")
                shutil.copy2(source, active)
                _backend_log.info(f"Activated model: {model_name}")
                import src.core.vision_yolo as vision_yolo
                vision_yolo._yolo_detector = None
                vision_yolo._yolo_enemy_detector = None
                _yolo_quality_checked = False
                _validate_yolo_model()
                self._send_json({
                    "status": "ok",
                    "message": f"Activated: {model_name}",
                    "model": model_name,
                    "quality_score": _yolo_quality_score,
                    "quality_warning": _yolo_quality_warning,
                })

            else:
                self._send_json({"error": f"Unknown action: {action}"}, 400)

        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)


# ============================================================================
# Server setup (ThreadingMixIn from Bridger pattern)
# ============================================================================

class ThreadingMixIn:
    daemon_threads = True
    blocking_mode = False


class ZedsuHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        pass  # Suppress noise on broken connections


# ============================================================================
# Entry point
# ============================================================================

def main():
    global _app_config

    # Load config (ZedsuBackend owns config)
    try:
        from src.utils.config import load_config
        _app_config = load_config()
    except Exception as e:
        _backend_log.warning(f"Could not load config: {e}")
        _app_config = {}

    # D-11.5d-01: Do NOT auto-launch core on startup.
    # Core starts only when backend receives a "start" or "toggle" command.
    # (Removed _launch_core() from main())
    _backend_log.info("[STARTUP] Backend launched in IDLE state — awaiting start/toggle command")

    # Phase 11: Validate YOLO model quality on startup (D-11d-01)
    try:
        quality = _validate_yolo_model()
        if quality["warning"]:
            print(f"[WARNING] YOLO model quality low (F1={quality['score']:.1%}) — consider retraining")
    except Exception as e:
        print(f"[INFO] YOLO quality check skipped: {e}")

    # Start HTTP server
    server = ZedsuHTTPServer((HOST, PORT), ZedsuHandler)
    _backend_log.info(f"ZedsuBackend listening on http://{HOST}:{PORT}")
    print(f"ZedsuBackend running on http://{HOST}:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        if _core_instance:
            _core_instance.stop()
        server.shutdown()


if __name__ == '__main__':
    main()
