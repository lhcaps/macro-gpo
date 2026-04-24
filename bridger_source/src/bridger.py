"""
bridger.py — Fishing Automation Engine for Roblox

Detects fish bites via audio template matching (FFT cross-correlation)
and handles the fishing minigame via OCR (Tesseract), OpenCV template matching,
or pixel-based detection.

Run from source:
    python -m src.bridger
    (Or: python src/bridger.py when BridgerBackend is not running separately)
"""

import threading
import time
import os
import sys
import ctypes
import random
import math

import numpy as np
import pyautogui
import pyaudio
import scipy.signal as signal
from scipy.io import wavfile
from scipy.signal import resample_poly

import mss
import cv2
import keyboard
import mouse

from PIL import ImageGrab, Image

import pytesseract

# Disable pyautogui failsafe
pyautogui.FAILSAFE = False


# --- Tesseract path resolution ---
def _get_tesseract_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'tesseract', 'tesseract.exe')
    return r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def _get_tessdata_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'tesseract', 'tessdata')
    return r'C:\Program Files\Tesseract-OCR\tessdata'


# Set up tesseract
pytesseract.pytesseract.tesseract_cmd = _get_tesseract_path()
os.environ['TESSDATA_PREFIX'] = _get_tessdata_path()


# --- DPI awareness ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    pass
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass


# --- Module-level constants ---
if getattr(sys, 'frozen', False):
    _SCRIPT_DIR = os.path.dirname(sys.executable)
    _ASSETS_DIR = sys._MEIPASS
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _ASSETS_DIR = _SCRIPT_DIR

_TPL_DIR = os.path.join(_ASSETS_DIR, 'pics')
TEMPLATE_FILE = os.path.join(_TPL_DIR, 'bite_template.wav')

_PIXEL_REF_W = 1920
_PIXEL_REF_H = 1080

# Pixel anchor reference position (anchor pixel used for pixel detection mode)
_PIXEL_ANCHOR_POS = (959, 509)
_PIXEL_SEARCH_R = 10  # Search radius around anchor
_PIXEL_ANCHOR_RGB = (30, 30, 30)
_PIXEL_WHITE_RGB = (255, 255, 255)

# Letter key offsets: {letter: [(dx, dy), ...]}
_PIXEL_LETTER_CHECKS = {
    'r': [(-13, 17), (17, 33)],
    't': [(-15, 15), (17, 15)],
    'f': [(17, 16), (11, 42)],
    'g': [(-18, 43), (19, 42)],
}

# Pixel grab reference for coordinate scaling
_PIXEL_GRAB_REF_X = 928
_PIXEL_GRAB_REF_Y = 488
_PIXEL_GRAB_REF_W = 64
_PIXEL_GRAB_REF_H = 78


class FishingEngine:
    """
    Main fishing automation engine.

    Detects fish bites using audio FFT template matching (scipy + numpy).
    Handles the Roblox fishing minigame using Tesseract OCR, OpenCV template
    matching, or pixel-based letter detection.
    """

    def __init__(self, log_fn=None, status_fn=None, score_fn=None,
                 ocr_fn=None, webhook_fn=None, force_close_fn=None):
        self.log_fn = log_fn or (lambda msg, level=None: None)
        self.status_fn = status_fn or (lambda s: None)
        self.score_fn = score_fn or (lambda c, r: None)
        self.webhook_fn = webhook_fn or (lambda s, e, d: None)
        self.force_close_fn = force_close_fn or (lambda cfg: None)

        # Default settings
        self.cfg = {}
        self.ocr_tolerance = 40
        self.minigame_scan_delay = 0.05
        self.scan_delay_random = False
        self.scan_delay_min = 0.1
        self.scan_delay_max = 0.5
        self.detect_method = 'numpy'  # 'numpy', 'cv', or 'pixel'
        self.pixel_tolerance = 0
        self.pixel_anchor_tolerance = 0
        self.pixel_scan_delay = 0.03

        self._cv_templates = {}
        self._fp_templates = {}
        self._templates_ready = False

        self.focus_keywords = ['roblox']

        self.monitor_index = 1

        # Audio
        self.audio_device_index = -1
        self._active_device_name = ''

        # Minigame defaults
        self.ocr_region = [0.474, 0.47, 0.531, 0.551]
        self.bite_event = threading.Event()
        self.stop_event = threading.Event()

        # Stats
        self._blank_exit_streak = 0
        self._timeout_streak = 0
        self.cast_num = 0
        self.stat_minigame = 0
        self.stat_no_minigame = 0
        self.stat_timeouts = 0
        self.stat_chest = 0
        self.stat_mare = 0
        self.stat_arrow_shard = 0
        self.running = False

    def log(self, msg, level='info'):
        self.log_fn(msg, level)

    def set_status(self, text):
        self.status_fn(text)

    def _gcd(self, a, b):
        while b:
            a, b = b, a % b
        return a

    def _load_template(self):
        try:
            sr, data = wavfile.read(TEMPLATE_FILE)
        except FileNotFoundError:
            self.log(f"{TEMPLATE_FILE} not found!", 'err')
            raise

        if len(data.shape) > 1:
            data = data.mean(axis=1)  # Stereo -> Mono

        # Trim silence from end (below 1% of max amplitude)
        threshold = data.max() * 0.01
        trimmed = data
        for i in range(len(trimmed) - 1, -1, -1):
            if abs(trimmed[i]) > threshold:
                trimmed = trimmed[:i + 1]
                break

        # Resample to 48000 Hz
        if sr != 48000:
            gcd_val = self._gcd(sr, 48000)
            trimmed = resample_poly(trimmed, 48000 // gcd_val, sr // gcd_val)
            sr = 48000

        self.log(f"  Trimmed template to {len(trimmed) / sr:.2f}s (removed silence)")
        self.tmpl_sr = sr
        self.tmpl_raw = trimmed
        self.log(f"[OK] Template loaded ({len(trimmed) / sr:.2f}s @ {sr} Hz)")
        return sr, trimmed, len(trimmed) / sr

    def _init_audio_pipeline(self, capture_sr):
        if self.tmpl_sr != capture_sr:
            gcd_val = self._gcd(self.tmpl_sr, capture_sr)
            self.template = resample_poly(self.tmpl_raw,
                                          capture_sr // gcd_val,
                                          self.tmpl_sr // gcd_val)
            self.log(f"  Resampled template {self.tmpl_sr} Hz -> {capture_sr} Hz")
        else:
            self.template = self.tmpl_raw

        self.fft_len = len(self.template)
        self.tmpl_std_val = np.std(self.template)

        # Pre-compute FFT of template
        self._T_FFT = np.fft.rfft(self.template)
        self.buf_lock = threading.Lock()
        self.audio_buf = np.zeros(self.fft_len * 2, dtype=np.float32)
        self.bite_valid_after = 0  # timestamp before which bites are ignored

    def get_loopback_devices(self):
        devices = []
        try:
            import pyaudiowpatch as pyaudio
            pa = pyaudio.PyAudio()
            for i in range(pa.get_device_count()):
                try:
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0 and 'loopback' in info['name'].lower():
                        devices.append({
                            'index': i,
                            'name': info['name'],
                            'sr': int(info['defaultSampleRate']),
                            'ch': info['maxInputChannels'],
                        })
                except Exception:
                    pass
            pa.terminate()
        except ImportError:
            pass
        return devices

    def _run_audio(self):
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            self.log("[ERROR] No WASAPI loopback device found!", 'err')
            return

        pa = pyaudio.PyAudio()
        device_index = self.audio_device_index

        if device_index < 0:
            for i in range(pa.get_device_count()):
                try:
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0 and 'loopback' in info['name'].lower():
                        device_index = i
                        self._active_device_name = info['name']
                        self.log(f"[AUDIO] Loopback: {info['name']} ({int(info['defaultSampleRate'])} Hz, {info['maxInputChannels']}ch)")
                        break
                except Exception:
                    pass

        if device_index < 0:
            self.log("[ERROR] No WASAPI loopback device found!", 'err')
            pa.terminate()
            return

        sr = int(pa.get_device_info_by_index(device_index)['defaultSampleRate'])

        self._init_audio_pipeline(sr)
        self.audio_buf = np.zeros(self.fft_len * 2, dtype=np.float32)

        def audio_callback(in_data, frame_count, time_info, status):
            if status:
                self.log(f"[AUDIO ERROR] {in_data}", 'ignore')
            data = np.frombuffer(in_data, dtype=np.float32)
            with self.buf_lock:
                self.audio_buf = np.concatenate([self.audio_buf[-self.fft_len:], data])
            return (in_data, pyaudio.paContinue)

        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=sr,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.fft_len,
            stream_callback=audio_callback
        )

        stream.start_stream()
        self.log("[AUDIO] Capture started — listening to your speakers")

        while not self.stop_event.is_set():
            time.sleep(0.05)
            with self.buf_lock:
                buf = self.audio_buf.copy()

            if len(buf) < self.fft_len:
                continue

            # FFT cross-correlation
            buf_fft = np.fft.rfft(buf[-self.fft_len:])
            xcorr = np.fft.irfft(buf_fft * self._T_FFT.conj())[-self.fft_len:]
            corr = np.max(xcorr) / (np.std(buf[-self.fft_len:]) * self.tmpl_std_val + 1e-10)
            rms = np.sqrt(np.mean(buf[-self.fft_len:] ** 2))

            self.score_fn(corr, rms)

            if corr > self.cfg.get('match_threshold', 0.3) or rms > self.cfg.get('rms_threshold', 0.015):
                if time.time() > self.bite_valid_after:
                    self.log(f"  --> BITE TRIGGERED  corr={corr:.3f}  rms={rms:.4f}")
                    self.bite_event.set()
                    self.bite_valid_after = time.time() + 2.0  # debounce 2s

        stream.stop_stream()
        stream.close()
        pa.terminate()

    def _is_game_focused(self):
        try:
            GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
            GetWindowTextW = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW

            hwnd = GetForegroundWindow()
            length = GetWindowTextLengthW(hwnd)
            if length == 0:
                return False
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.lower()
            return any(kw in title for kw in self.focus_keywords)
        except Exception:
            return True

    def _get_monitor(self):
        monitors = mss.mss().monitors
        if self.monitor_index < len(monitors):
            return monitors[self.monitor_index]
        return monitors[0]

    def _capture(self, region=None):
        try:
            monitor = self._get_monitor()
            with mss.mss() as sct:
                if region:
                    mon = monitor
                    sw, sh = mon['width'], mon['height']
                    sx, sy = mon['left'], mon['top']
                    r = (
                        int(sx + region[0] * sw),
                        int(sy + region[1] * sh),
                        int(sx + region[2] * sw),
                        int(sy + region[3] * sh),
                    )
                    img = sct.grab(r)
                    return Image.frombytes('RGB', img.size, img.rgb)
                return sct.grab(monitor)
        except Exception as e:
            self.log(f"mss screenshot failed: {e}, trying ImageGrab")
            try:
                return ImageGrab.grab()
            except Exception as e2:
                self.log(f"ImageGrab also failed: {e2}", 'err')
                return None

    def _region_bbox(self, region):
        mon = self._get_monitor()
        sw, sh = mon['width'], mon['height']
        sx, sy = mon['left'], mon['top']
        return sw, sh, sx, sy

    def _get_scan_delay(self):
        if self.scan_delay_random:
            return random.uniform(self.scan_delay_min, self.scan_delay_max)
        return self.minigame_scan_delay

    # --- Minigame detection dispatch ---
    def _check_minigame(self):
        if self.detect_method == 'pixel':
            return self._check_minigame_pixel()
        elif self.detect_method == 'cv':
            return self._check_minigame_cv()
        else:
            return self._check_minigame_ocr()

    def _check_minigame_ocr(self):
        self.log("  *** MINIGAME — Tesseract OCR active ***", 'warn')
        presses = 0
        total_scans = 0
        blank_count = 0
        blank_exit = self.cfg.get('mg_blank_exit', 5)

        while not self.stop_event.is_set():
            if not self._is_game_focused():
                self.log("  [OCR] SKIP — game not focused")
                time.sleep(0.5)
                continue

            mon = self._get_monitor()
            sw, sh = mon['width'], mon['height']
            region = self.ocr_region
            img = self._capture(region)
            if img is None:
                continue

            gray = np.array(img.convert('L'))
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            img_bin = Image.fromarray(binary)

            raw_text = pytesseract.image_to_string(
                img_bin,
                config='--psm 8 -c tessedit_char_whitelist=TGFR'
            ).strip()

            total_scans += 1
            detected = None
            for char in raw_text:
                if char.upper() in 'TGFR':
                    detected = char.upper()
                    break

            delay = self._get_scan_delay()
            if detected:
                self.log(f"  [OCR] PRESS {detected}  presses={presses}")
                pyautogui.press(detected.lower())
                presses += 1
                blank_count = 0
            else:
                blank_count += 1
                self.log(f"  [OCR] blank {blank_count}/{blank_exit}  raw={repr(raw_text[:4])}")

            if blank_count >= blank_exit:
                self.log(f"  [OCR] Exit — blanks={blank_count}  scans={total_scans}  presses={presses}")
                break

            time.sleep(delay)

        return presses

    def _check_minigame_cv(self):
        if not self._templates_ready:
            self.load_cv_templates()
        method_label = 'Numpy' if self.detect_method == 'numpy' else 'OpenCV'
        self.log(f"  *** MINIGAME — {method_label} active ***", 'warn')
        presses = 0
        total_scans = 0
        blank_count = 0
        blank_exit = self.cfg.get('mg_blank_exit', 5)
        thr = self.cfg.get('cv_threshold', 0.7)

        while not self.stop_event.is_set():
            if not self._is_game_focused():
                time.sleep(0.5)
                continue

            img = self._capture(self.ocr_region)
            if img is None:
                continue

            letter, score = self._detect_letter(img, method=self.detect_method)
            total_scans += 1
            delay = self._get_scan_delay()

            if letter and score >= thr:
                self.log(f"  [{method_label[:2]}] PRESS {letter}  score={score:.3f}  presses={presses}")
                pyautogui.press(letter.lower())
                presses += 1
                blank_count = 0
            else:
                blank_count += 1
                self.log(f"  [{method_label[:2]}] blank {blank_count}/{blank_exit}  best={score:.3f}")

            if blank_count >= blank_exit:
                self.log(f"  [{method_label[:2]}] Exit — blanks={blank_count}  scans={total_scans}  presses={presses}")
                break

            time.sleep(delay)

        return presses

    def _check_minigame_pixel(self):
        self.log("  *** MINIGAME — Pixel detection active ***", 'warn')
        presses = 0
        blank_count = 0
        blank_exit = self.cfg.get('mg_blank_exit', 5)

        while not self.stop_event.is_set():
            if not self._is_game_focused():
                time.sleep(0.5)
                continue

            mon = self._get_monitor()
            sw, sh, ox, oy = self._region_bbox(mon)

            detected = self._detect_pixel_letter(
                monitor_index=self.monitor_index,
                sw=sw, sh=sh, ox=ox, oy=oy
            )
            delay = self._get_scan_delay()

            if detected:
                pyautogui.press(detected.lower())
                presses += 1
                blank_count = 0
            else:
                blank_count += 1

            if blank_count >= blank_exit:
                self.log(f"  [PIXEL] Exit — blanks={blank_count}  presses={presses}")
                break

            time.sleep(delay)

        return presses

    # --- CV / Numpy template detection ---
    _CV_NORM_SIZE = (40, 40)
    _FP_SIZE = (16, 16)

    def load_cv_templates(self):
        template_dir = _TPL_DIR
        letters = ['t', 'g', 'f', 'r']

        for letter in letters:
            for suffix in ['', '_a', '_b']:
                fname = f"tpl_{letter}{suffix}.png"
                path = os.path.join(template_dir, fname)
                if not os.path.exists(path):
                    continue
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                crop = self._largest_interior_blob(binary)
                if crop is None:
                    continue
                cv_template = cv2.resize(crop, self._CV_NORM_SIZE)
                fp = self._build_fingerprint(crop)
                self._cv_templates[f"{letter}{suffix}"] = cv_template
                self._fp_templates[f"{letter}{suffix}"] = fp

        self._templates_ready = True
        self.log(f"[OK] CV templates loaded: {list(self._cv_templates.keys())}")

    def _largest_interior_blob(self, binary_img):
        h, w = binary_img.shape
        mask = binary_img.copy()
        border = (mask[0, :] == 255) | (mask[-1, :] == 255) | (mask[:, 0] == 255) | (mask[:, -1] == 255)
        if border.any():
            return binary_img
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return binary_img
        largest = max(contours, key=cv2.contourArea)
        x, y, cw, ch = cv2.boundingRect(largest)
        return binary_img[y:y+ch, x:x+cw]

    def _prepare_letter_crop(self, binary_img):
        cropped = self._largest_interior_blob(binary_img)
        if cropped is None or cropped.size == 0:
            return None
        kernel = np.ones((3, 3), np.uint8)
        closed = cv2.morphologyEx(cropped, cv2.MORPH_CLOSE, kernel)
        resized = cv2.resize(closed, self._CV_NORM_SIZE)
        return resized

    def _build_fingerprint(self, binary_img):
        resized = cv2.resize(binary_img, self._FP_SIZE)
        norm = resized.astype(np.float32) / 255.0
        return norm.flatten()

    def _detect_letter(self, img, method='numpy'):
        gray = np.array(img.convert('L'))
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        crop = self._prepare_letter_crop(binary)
        if crop is None:
            return (None, 0.0)

        if method == 'numpy':
            fp = self._build_fingerprint(crop)
            return self._detect_letter_fp(fp)
        else:
            best = (None, -1)
            for name, template in self._cv_templates.items():
                letter = name[0].upper()
                res = cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED)
                score = res.max()
                if score > best[1]:
                    best = (letter, score)
            return best

    def _detect_letter_fp(self, fp_crop):
        best = (None, -1)
        for name, fp_template in self._fp_templates.items():
            letter = name[0].upper()
            score = np.dot(fp_crop.flatten(), fp_template)
            if score > best[1]:
                best = (letter, score)
        return best

    # --- Pixel detection ---
    def _detect_pixel_letter(self, monitor_index, sw, sh, ox, oy):
        anchor = self._find_pixel_anchor(monitor_index, sw, sh, ox, oy)
        if anchor is None:
            return None

        sx = sw / _PIXEL_REF_W
        sy = sh / _PIXEL_REF_H

        grab_x = int(anchor[0] - ox - _PIXEL_GRAB_REF_X * sx)
        grab_y = int(anchor[1] - oy - _PIXEL_GRAB_REF_Y * sy)
        grab_w = int(_PIXEL_GRAB_REF_W * sx)
        grab_h = int(_PIXEL_GRAB_REF_H * sy)

        with mss.mss() as sct:
            img = sct.grab((grab_x, grab_y, grab_x + grab_w, grab_y + grab_h))
            arr = np.array(img)[:, :, :3]

        white_rgb = _PIXEL_WHITE_RGB
        tol = self.pixel_tolerance

        for letter, offsets in _PIXEL_LETTER_CHECKS.items():
            for dx, dy in offsets:
                px = int(anchor[0] - ox + dx * sx)
                py = int(anchor[1] - oy + dy * sy)
                lx = px - grab_x
                ly = py - grab_y
                if 0 <= lx < arr.shape[1] and 0 <= ly < arr.shape[0]:
                    pixel = arr[ly, lx]
                    if all(abs(int(pixel[i]) - white_rgb[i]) <= tol for i in range(3)):
                        return letter
        return None

    def _find_pixel_anchor(self, monitor_index, sw, sh, ox, oy):
        rx = int(_PIXEL_ANCHOR_POS[0] * sw / _PIXEL_REF_W)
        ry = int(_PIXEL_ANCHOR_POS[1] * sh / _PIXEL_REF_H)

        grab_x = rx - ox - _PIXEL_SEARCH_R
        grab_y = ry - oy - _PIXEL_SEARCH_R
        grab_w = _PIXEL_SEARCH_R * 2
        grab_h = _PIXEL_SEARCH_R * 2

        with mss.mss() as sct:
            monitor = sct.monitors[monitor_index]
            img = sct.grab((grab_x, grab_y, grab_x + grab_w, grab_y + grab_h))
            arr = np.array(img)[:, :, :3]

        target_rgb = _PIXEL_ANCHOR_RGB
        tol = self.pixel_anchor_tolerance

        for dy in range(arr.shape[0]):
            for dx in range(arr.shape[1]):
                pixel = arr[dy, dx]
                if all(abs(int(pixel[i]) - target_rgb[i]) <= tol for i in range(3)):
                    return (dx - _PIXEL_SEARCH_R + rx - ox, dy - _PIXEL_SEARCH_R + ry - oy)
        return None

    # --- Fishing loop ---
    def _overlay_click_pos(self):
        if self.cfg.get('cast_pos_custom', False):
            mon = self._get_monitor()
            x = int(self.cfg['cast_pos_x'] * mon['width'])
            y = int(self.cfg['cast_pos_y'] * mon['height'])
            return x, y

        mon = self._get_monitor()
        sw, sh = mon['width'], mon['height']
        region = self.ocr_region
        x = int((region[0] + 0.01) * sw)
        y = int((region[3] - 0.01) * sh)
        return x, y

    def _focus_roblox(self):
        try:
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_long, ctypes.c_long)
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
            SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow

            results = []
            def callback(hwnd, lparam):
                length = GetWindowTextLength(hwnd)
                if length == 0:
                    return True
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                if 'roblox' in buff.value.lower():
                    results.append(hwnd)
                return True
            EnumWindows(EnumWindowsProc(callback), 0)
            if results:
                SetForegroundWindow(results[0])
        except Exception:
            pass

    def _apply_bait(self):
        bait_key = self.cfg.get('bait_key', '2')
        rod_key = self.cfg.get('rod_key', '1')
        mon = self._get_monitor()
        sw, sh = mon['width'], mon['height']
        region = self.ocr_region

        pyautogui.press(bait_key)
        time.sleep(0.2)

        cx = int((region[2] + 0.01) * sw)
        cy = int((region[3] + 0.01) * sh)
        pyautogui.click(cx, cy)
        time.sleep(0.3)

        pyautogui.press(rod_key)

    def _fishing_loop(self):
        self._first_cast = True
        timeout_limit = self.cfg.get('timeout_streak_webhook', 5)
        force_close = self.cfg.get('timeout_streak_force_close', False)

        while not self.stop_event.is_set():
            self.cast_num += 1
            self.log(f"[Cast #{self.cast_num}] ── Starting cast ──")

            if self._first_cast:
                self._focus_roblox()
                self._first_cast = False

            self.set_status("CASTING #{}".format(self.cast_num))
            if self.cfg.get('use_bait', True):
                self._apply_bait()
            else:
                cx, cy = self._overlay_click_pos()
                pyautogui.moveTo(cx, cy)
                pyautogui.click()
                pyautogui.press(self.cfg.get('rod_key', '1'))

            cast_wait = self.cfg.get('cast_wait', 1.0)
            time.sleep(cast_wait)
            self.set_status("WAITING FOR BITE")
            self.log("  Rod in water — listening for bite sound...")

            # Wait for bite or timeout (35s)
            bite_timeout = 35.0
            timeout_start = time.time()
            bite_detected = False

            while time.time() - timeout_start < bite_timeout:
                if self.stop_event.is_set():
                    return
                if self.bite_event.wait(timeout=0.5):
                    self.bite_event.clear()
                    bite_detected = True
                    break

            if not bite_detected:
                self._timeout_streak += 1
                self.stat_timeouts += 1
                self.log(f"  No bite after 35s (timeout #{self._timeout_streak}) — recasting.", 'warn')

                if self._timeout_streak >= timeout_limit:
                    if self.cfg.get('webhook_enabled', False):
                        self.webhook_fn(self.cfg, 'timeout', {'streak': self._timeout_streak})
                    if force_close:
                        self.force_close_fn(self.cfg)
                    self.stop()
                    return
                continue

            # Bite detected!
            self._timeout_streak = 0
            self.bite_event.clear()
            self.set_status("BITE DETECTED!")
            self.log("  Bite sound detected! Clicking to reel in...")
            pyautogui.click()

            # Wait for minigame window
            verify_window = self.cfg.get('verify_window', 0.7)
            time.sleep(verify_window)

            if self.cfg.get('skip_minigame', False):
                self.set_status("MINIGAME — SKIPPING")
                time.sleep(self.cfg.get('minigame_dur', 10.0))
                continue

            detected = self._check_catch_notification()
            if detected:
                self.set_status("MINIGAME ACTIVE")
                self.log("  Minigame prompt detected — starting key handler...")
                self.stat_minigame += 1
                self._blank_exit_streak = 0
                presses = self._check_minigame()

                if presses > 8:
                    self.stat_arrow_shard += 1
                    self.set_status("ARROW SHARD!")
                    self.log(f"  *** ARROW SHARD ({presses} presses) ***")
                    if self.cfg.get('webhook_enabled'):
                        self.webhook_fn(self.cfg, 'arrow_shard', {'presses': presses})
                elif presses > 4:
                    self.stat_mare += 1
                    self.set_status("MARE!")
                    self.log(f"  Mare caught ({presses} presses)")
                elif presses > 0:
                    self.stat_chest += 1
                    self.set_status("CHEST!")
                    self.log(f"  Chest ({presses} presses)")
            else:
                self.stat_no_minigame += 1
                self.set_status("No minigame — reel complete")
                self.log("  No minigame — fish reeled in directly.")

            # Walk/repo sequence
            if self.cfg.get('repo_enabled', False):
                self.set_status("WALKING...")
                sequence = self.cfg.get('walk_sequence', [])
                for step_name in sequence:
                    recording = self.cfg.get('walk_recordings', {}).get(step_name, [])
                    duration = self.cfg.get(f'repo_step_duration_{step_name}', 5.0)
                    self.log(f"  [REPO] {step_name} for {duration}s...")
                    time.sleep(duration)

            between = self.cfg.get('between_casts', 1.5)
            self.set_status("Between casts...")
            time.sleep(between)

    def _check_catch_notification(self):
        if not self._is_game_focused():
            return None

        region = self.ocr_region
        mon = self._get_monitor()
        sw, sh = mon['width'], mon['height']

        img = self._capture(region)
        if img is None:
            return None

        gray = np.array(img.convert('L'))
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        img_bin = Image.fromarray(binary)

        text = pytesseract.image_to_string(
            img_bin,
            config='--psm 8 -c tessedit_char_whitelist=TGFR'
        ).strip()

        for char in text:
            if char.upper() in 'TGFR':
                return char.upper()
        return None

    def start(self):
        if self.running:
            return

        if not os.path.exists(TEMPLATE_FILE):
            self.log(f"[ERROR] {TEMPLATE_FILE} missing — cannot start!", 'err')
            return

        self.log("[START] Launching audio capture thread...")
        self.log("[START] Launching fishing loop thread...")
        self.log("[START] Macro running — switch to Roblox!", 'ok')

        self.stop_event.clear()
        self.bite_event.clear()
        self.running = True
        self._first_cast = True
        self._timeout_streak = 0
        self._blank_exit_streak = 0

        self._load_template()

        threading.Thread(target=self._run_audio, daemon=True, name='AudioThread').start()
        threading.Thread(target=self._fishing_loop, daemon=True, name='FishingLoop').start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        self.bite_event.set()
        self.log("[STOP] Cast loop interrupted — macro stopped.", 'warn')
        self.set_status("STOPPED")
