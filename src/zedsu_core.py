"""
ZedsuCore — Pure bot logic library for GPO BR.

Callable as a library — no GUI imports, no Tkinter, no pyautogui in hot path.
Communicates with outer tiers via CoreCallbacks (Protocol interface).

Architecture:
- Tier 1 of the 3-tier Zedsu architecture
- No direct file logging — uses callbacks.log()
- No direct Discord — uses callbacks.discord()
- Config accessed via callbacks.config()
- Entry points: create_core(), ZedsuCore.start/stop/pause/resume/get_state()
"""
import os
import random
import sys
import threading
import time
from enum import Enum, auto

import pydirectinput

# pyautogui used only for screenshot in post_match (not in hot path)
import pyautogui  # noqa: F401 — used in handle_post_match only

try:
    import mss
    import numpy as np
    import cv2
    _MSS_AVAILABLE = True
    _CV2_AVAILABLE = True
except ImportError:
    mss = None
    np = None
    cv2 = None
    _MSS_AVAILABLE = False
    _CV2_AVAILABLE = False

from typing import Optional

from src.zedsu_core_callbacks import CoreCallbacks, NoOpCallbacks

# Import utility wrappers that don't need app
from src.core.controller import human_click, sleep_with_stop


# ============================================================================
# PHASE 5: COMBAT STATE MACHINE
# ============================================================================

class CombatState(Enum):
    IDLE = auto()
    SCANNING = auto()
    APPROACH = auto()
    ENGAGED = auto()
    FLEEING = auto()
    SPECTATING = auto()
    POST_MATCH = auto()


class CombatStateMachine:
    """
    Intelligent combat FSM for GPO BR.

    Transition rules:
    IDLE → SCANNING: match starts (ultimate bar visible)
    SCANNING → APPROACH: enemy detected (green HP bar or frame diff)
    SCANNING → ENGAGED: direct close-range signal
    APPROACH → ENGAGED: enemy close enough (green HP bar detected)
    ENGAGED → FLEEING: player HP drops below threshold
    ENGAGED → SCANNING: enemy lost (no signals for N frames)
    ENGAGED → SPECTATING: death detected
    FLEEING → SCANNING: player HP recovered
    FLEEING → SPECTATING: player died
    Any → SPECTATING: death confirmed
    SPECTATING → POST_MATCH: results screen
    POST_MATCH → IDLE: lobby
    """

    def __init__(self, engine):
        self.engine = engine
        self.state = CombatState.IDLE
        self._state_enter_time = 0
        self._last_enemy_detected = 0
        self._last_incombat_time = 0
        self._kill_count = 0
        self._consecutive_engaged_frames = 0
        self._consecutive_no_signal_frames = 0
        self._scan_direction = 1
        self._scan_timer = 0
        self._last_kill_detected = False
        self._last_yolo_scan_time = 0

        cfg = engine.config
        self.disengage_timeout_sec = cfg.get("combat_settings", {}).get("disengage_timeout_sec", 5.0)
        self.fleeing_hp_threshold = cfg.get("combat_settings", {}).get("fleeing_hp_threshold", 0.25)
        self.dodge_chance = cfg.get("combat_settings", {}).get("dodge_chance", 0.12)
        self.camera_scan_interval = cfg.get("combat_settings", {}).get("camera_scan_interval", 0.5)
        self.kill_steal_resilient = cfg.get("combat_settings", {}).get("kill_steal_resilient", True)

    @property
    def state_name(self):
        return self.state.name

    def _transition_to(self, new_state):
        old = self.state
        self.state = new_state
        self._state_enter_time = time.time()
        self.engine.log(f"[COMBAT] {old.name} → {new_state.name}")

    def update(self, signals: dict) -> dict:
        """
        Called every combat tick. signals dict from CombatSignalDetector.scan_all_signals().
        Returns action dict: {action: str, data: dict}
        """
        now = time.time()
        action = {"action": "none", "data": {}}

        if self.state == CombatState.IDLE:
            if signals.get("in_combat"):
                self._transition_to(CombatState.SCANNING)
            elif signals.get("spectating"):
                self._transition_to(CombatState.SPECTATING)

        elif self.state == CombatState.SCANNING:
            if signals.get("close_range"):
                self._transition_to(CombatState.ENGAGED)
            elif signals.get("enemy_detected"):
                self._transition_to(CombatState.APPROACH)
            elif signals.get("spectating"):
                self._transition_to(CombatState.SPECTATING)
            elif now - self._state_enter_time > 15:
                self.engine.log("[COMBAT] SCANNING timeout → ENGAGED (fallback)")
                self._transition_to(CombatState.ENGAGED)

        elif self.state == CombatState.APPROACH:
            if signals.get("close_range"):
                self._transition_to(CombatState.ENGAGED)
            elif now - self._last_enemy_detected > 5:
                self._transition_to(CombatState.SCANNING)
            elif signals.get("spectating"):
                self._transition_to(CombatState.SPECTATING)

        elif self.state == CombatState.ENGAGED:
            if signals.get("player_hp_low"):
                self._transition_to(CombatState.FLEEING)
            elif not signals.get("enemy_signals") and self._consecutive_no_signal_frames > 10:
                self._transition_to(CombatState.SCANNING)
            elif signals.get("spectating"):
                self._transition_to(CombatState.SPECTATING)
            else:
                self._consecutive_no_signal_frames = 0

            if signals.get("enemy_signals"):
                self._last_enemy_detected = now
                self._consecutive_engaged_frames += 1
            else:
                self._consecutive_engaged_frames = 0

            if signals.get("kill_detected") and not self._last_kill_detected:
                self._kill_count += 1
                self.engine.log(f"[COMBAT] Kill #{self._kill_count}!")
                self._last_kill_detected = True
            elif not signals.get("kill_detected"):
                self._last_kill_detected = False

        elif self.state == CombatState.FLEEING:
            if not signals.get("player_hp_low"):
                self._transition_to(CombatState.SCANNING)
            elif signals.get("spectating"):
                self._transition_to(CombatState.SPECTATING)
            elif now - self._state_enter_time > self.disengage_timeout_sec:
                self.engine.log("[COMBAT] Flee timeout — returning to scan")
                self._transition_to(CombatState.SCANNING)

        elif self.state == CombatState.SPECTATING:
            if signals.get("post_match"):
                self._transition_to(CombatState.POST_MATCH)
            elif signals.get("in_combat"):
                self._transition_to(CombatState.SCANNING)

        elif self.state == CombatState.POST_MATCH:
            self._transition_to(CombatState.IDLE)

        # Execute state behavior
        if self.state == CombatState.SCANNING:
            action = self._scan_behavior(signals)
        elif self.state == CombatState.ENGAGED:
            action = self._engaged_behavior(signals)
        elif self.state == CombatState.FLEEING:
            action = self._flee_behavior(signals)

        return action

    def _scan_behavior(self, signals: dict) -> dict:
        if time.time() - self._scan_timer < self.camera_scan_interval:
            return {"action": "none"}
        self._scan_timer = time.time()
        keys = self.engine.config.get("keys", {})
        forward = keys.get("forward", "w")
        right = keys.get("right", "d")
        if self._scan_direction == 1:
            pydirectinput.keyDown(right)
            time.sleep(0.3)
            pydirectinput.keyUp(right)
            self._scan_direction = -1
        else:
            pydirectinput.keyDown(forward)
            time.sleep(0.3)
            pydirectinput.keyUp(forward)
            self._scan_direction = 1
        return {"action": "scan", "direction": self._scan_direction}

    def _engaged_behavior(self, signals: dict) -> dict:
        keys = self.engine.config.get("keys", {})
        slot1 = keys.get("slot_1", "1")
        dodge = keys.get("backward", "s")
        if self._consecutive_engaged_frames % 5 == 0:
            pydirectinput.press(slot1)
        if random.random() < self.dodge_chance:
            pydirectinput.keyDown(dodge)
            time.sleep(0.15)
            pydirectinput.keyUp(dodge)
        return {"action": "combat", "kills": self._kill_count}

    def _flee_behavior(self, signals: dict) -> dict:
        keys = self.engine.config.get("keys", {})
        backward = keys.get("backward", "s")
        pydirectinput.keyDown(backward)
        time.sleep(0.4)
        pydirectinput.keyUp(backward)
        return {"action": "flee"}

    def get_status(self) -> dict:
        return {
            "state": self.state.name,
            "kills": self._kill_count,
            "engaged_frames": self._consecutive_engaged_frames,
            "state_enter_time": self._state_enter_time,
            "scan_direction": self._scan_direction,
        }

    def on_match_start(self):
        self._transition_to(CombatState.SCANNING)

    def on_death(self):
        self._transition_to(CombatState.SPECTATING)

    def on_results_screen(self):
        self._transition_to(CombatState.POST_MATCH)

    def on_lobby(self):
        self._transition_to(CombatState.IDLE)
        self._kill_count = 0


# ============================================================================
# Internal BotEngine (extracted from src/core/bot_engine.py)
# Replaces self.app.* references with self._callbacks.*
# ============================================================================

class _ZedsuBotEngine:
    """
    Inner bot engine. Same logic as BotEngine but uses self._callbacks instead of self.app.
    """

    def __init__(self, callbacks: CoreCallbacks):
        self._callbacks = callbacks
        self.stop_requested = False
        self.last_leave_click_time = 0
        self.last_punch_time = 0
        self.match_start_time = 0
        self.last_lobby_log_time = 0
        self.last_focus_log_time = 0
        self.last_no_detection_log_time = 0
        self.last_slot_warning_time = 0
        self.last_combat_asset_log_time = 0
        self.last_match_hint_log_time = 0
        self.last_melee_confirm_time = 0
        self.last_wide_combat_scan_time = 0
        self.provisional_melee_until = 0
        self.combat_asset_miss_count = 0
        self.consecutive_melee_failures = 0
        self.last_melee_fallback_log_time = 0
        self.match_wait_transition_logged = False
        self.consecutive_return_prompt_scans = 0
        self.consecutive_spectate_checks = 0
        self.match_active = False
        self.cached_search_region = None
        self.cached_search_region_time = 0
        self.visibility_cache = {}
        self._combat_detector = None
        self._combat_sm = None
        self._combat_tick_interval = 0.5
        self._last_combat_tick = 0
        self._match_count = 0

    @property
    def config(self) -> dict:
        return self._callbacks.config()

    def is_running(self) -> bool:
        return self._callbacks.is_running() and not self.stop_requested

    def log(self, msg, is_error=False):
        level = "error" if is_error else "info"
        self._callbacks.log(msg, level)

    def sleep(self, seconds):
        return self._callbacks.sleep(seconds)

    def start(self):
        self.stop_requested = False
        self.consecutive_return_prompt_scans = 0
        self.consecutive_melee_failures = 0
        self.consecutive_spectate_checks = 0
        self.match_wait_transition_logged = False
        self.invalidate_runtime_caches(clear_region=True)
        self._combat_detector = None
        self._combat_sm = None
        self._last_combat_tick = 0

    def stop(self):
        self.stop_requested = True

    def _ensure_combat_system(self):
        """Lazily initialize combat detector and state machine."""
        if self._combat_detector is None:
            self._combat_detector = _get_combat_detector(self.config)
        if self._combat_sm is None:
            self._combat_sm = CombatStateMachine(self)

    def bot_loop(self):
        """Main entry point — runs in daemon thread."""
        self.start()
        self.log("Bot loop started")
        self._callbacks.status("IDLE", "#475569")

        while self.is_running():
            try:
                if not self.ensure_game_focused():
                    self._callbacks.status("WAITING FOR GAME WINDOW", "#b45309")
                    self.sleep(1.0)
                    continue

                self._callbacks.status("SCANNING LOBBY", "#2563eb")
                search_context = self.build_search_context()

                if self.is_visible("ultimate", search_context=search_context):
                    self.log("Ultimate bar detected. Starting combat.")
                    self.on_match_detected()
                    self._callbacks.status("MELEE LOOP", "#16a34a")
                    self.consecutive_return_prompt_scans = 0

                    if self.config.get("combat_settings", {}).get("smart_combat_enabled", True):
                        self._ensure_combat_system()
                        self._combat_sm.on_match_start()
                        melee_result = self._combat_loop()
                    else:
                        melee_result = self.auto_punch()

                    if melee_result == "post_match":
                        self.handle_post_match()
                    elif melee_result == "spectating":
                        self.handle_spectating()
                    else:
                        self.handle_match_waiting()

                else:
                    if time.time() - self.last_no_detection_log_time > 30:
                        self.log("No match indicators found in lobby scan.")
                        self.last_no_detection_log_time = time.time()

                    self.handle_lobby_scan()
                    self.consecutive_return_prompt_scans += 1

                self.sleep(self.config.get("scan_interval", 1.5))

            except Exception as exc:
                self.log(f"Loop error: {exc}", is_error=True)
                self.sleep(2.0)

        self._callbacks.status("IDLE", "#475569")
        self.log("Bot loop stopped.")

    # --- Combat loop ---
    def _combat_loop(self) -> str:
        """Smart combat loop using CombatStateMachine. Returns: 'post_match' | 'spectating'."""
        while self.is_running():
            now = time.time()
            if now - self._last_combat_tick < self._combat_tick_interval:
                self.sleep(0.1)
                continue
            self._last_combat_tick = now

            signals = self._combat_detector.scan_all_signals()
            action = self._combat_sm.update(signals)

            if action["action"] == "combat":
                if random.random() < self.config.get("combat_settings", {}).get("dodge_chance", 0.12):
                    keys = self.config.get("keys", {})
                    backward = keys.get("backward", "s")
                    pydirectinput.keyDown(backward)
                    self.sleep(0.15)
                    pydirectinput.keyUp(backward)
                slot1 = self.config.get("keys", {}).get("slot_1", "1")
                pydirectinput.press(slot1)

            elif action["action"] == "flee":
                keys = self.config.get("keys", {})
                backward = keys.get("backward", "s")
                pydirectinput.keyDown(backward)
                self.sleep(0.4)
                pydirectinput.keyUp(backward)

            elif action["action"] == "scan":
                pass  # Camera scan handled inside CombatStateMachine

            # Check for post_match / spectating
            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                return "post_match"
            if self.is_visible("ultimate"):
                pass  # Still in match
            else:
                if self.is_visible("spectating_icon", confidence=0.7):
                    return "spectating"

        return "stopped"

    # --- Helper methods (mirroring BotEngine) ---
    def build_search_context(self) -> dict:
        region = self._callbacks.get_search_region()
        if not region:
            return {}
        try:
            if _MSS_AVAILABLE and mss:
                with mss.mss() as sct:
                    screenshot = sct.grab(region)
                    img = np.array(screenshot)
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    return {"region": region, "image": img_bgr}
        except Exception:
            pass
        return {"region": region}

    def ensure_game_focused(self) -> bool:
        if not self.config.get("window_focus_required", True):
            return True
        title = str(self.config.get("game_window_title", "")).strip()
        if not title:
            return False
        from src.utils.windows import bring_window_to_foreground, find_window_by_title
        if find_window_by_title(title):
            if self.config.get("auto_focus_window", True):
                if bring_window_to_foreground(title):
                    self.invalidate_runtime_caches(clear_region=True)
                    self.log(f"Focused game window: {title}")
                    self._callbacks.status("FOCUSED GAME", "#0f766e")
                    self.sleep(0.6)
            return True
        return False

    def invalidate_runtime_caches(self, clear_region=False):
        self.cached_search_region = None
        self.visibility_cache = {}

    def is_visible(self, image_key: str, confidence: float = None, search_context: dict = None) -> bool:
        if search_context is None:
            search_context = self.build_search_context()
        ctx = search_context or self.build_search_context()
        region = ctx.get("region")
        img = ctx.get("image")
        if confidence is None:
            confidence = max(0.6, float(self.config.get("confidence", 0.8)) - 0.05)
        if img is None:
            return False
        result = _locate_image(image_key, self.config, confidence, region)
        return result is not None

    def safe_find_and_click(self, image_key: str, confidence: float = None) -> bool:
        region = self._callbacks.get_search_region()
        if region is None:
            return False
        img = None
        try:
            if _MSS_AVAILABLE and mss:
                with mss.mss() as sct:
                    screenshot = sct.grab(region)
                    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
        except Exception:
            return False
        result = _locate_image(image_key, self.config, confidence, region)
        if result:
            cx = result[0] + region["left"] + result[2] // 2
            cy = result[1] + region["top"] + result[3] // 2
            human_click(cx, cy, self.is_running, offset=2, move=True)
            return True
        return False

    def resolve_coordinate(self, key: str):
        from src.utils.config import resolve_coordinate as _resolve
        region = self._callbacks.get_search_region()
        rect = region if region else None
        return _resolve(self.config, key, window_rect=rect)

    def resolve_outcome_area(self):
        from src.utils.config import resolve_outcome_area as _resolve_outcome
        region = self._callbacks.get_search_region()
        rect = region if region else None
        return _resolve_outcome(self.config, window_rect=rect)

    def locate_image(self, image_key: str, confidence: float = None):
        region = self._callbacks.get_search_region()
        if region is None:
            return None
        return _locate_image(image_key, self.config, confidence, region)

    def on_match_detected(self, reason: str = ""):
        self._match_count += 1
        self.match_start_time = time.time()
        self.match_active = True
        msg = f"Match #{self._match_count} started"
        if reason:
            msg += f" ({reason})"
        self.log(msg)

    def handle_lobby_scan(self):
        now = time.time()
        if now - self.last_lobby_log_time > 45:
            mode = self.config.get("match_mode", "full").upper()
            self.log(f"Return to lobby button detected in {mode} mode.")
            self.last_lobby_log_time = now

        if self.config.get("match_mode") == "quick":
            if self.safe_find_and_click("return_to_lobby_alone"):
                self.last_leave_click_time = now
                self.log("Quick mode: clicked Return to Lobby.")

    def handle_match_waiting(self):
        self.log("Waiting for match to fully load.")
        self._callbacks.status("WAITING FOR MATCH", "#d97706")
        start_wait = time.time()
        last_log_time = 0

        while self.is_running():
            search_context = self.build_search_context()
            if self.is_visible("ultimate", search_context=search_context):
                self.log("Match fully loaded.")
                self.match_wait_transition_logged = False
                self.on_match_detected()
                self._callbacks.status("MELEE LOOP", "#16a34a")
                if self.config.get("combat_settings", {}).get("smart_combat_enabled", True):
                    self._ensure_combat_system()
                    melee_result = self._combat_loop()
                else:
                    melee_result = self.auto_punch()
                if melee_result == "post_match":
                    self.handle_post_match()
                    return
                elif melee_result == "spectating":
                    self.handle_spectating()
                    return
                return

            if time.time() - start_wait > 90:
                if not self.match_wait_transition_logged:
                    self.log("Match load is taking longer than usual. Staying in transition watch mode.")
                    self.match_wait_transition_logged = True
                self._callbacks.status("MATCH TRANSITION WATCH", "#b45309")

            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                self.match_wait_transition_logged = False
                self.on_match_detected("movement fallback")
                self._callbacks.status("IN MATCH", "#16a34a")
                if self.random_move() == "post_match":
                    self.handle_post_match()
                    return
            self.sleep(1.5)

    def handle_spectating(self):
        self.log("Spectate detected during melee loop.")
        self._callbacks.status("SPECTATING", "#7c3aed")
        start_wait = time.time()
        last_leave_logged = False

        while self.is_running():
            search_context = self.build_search_context()
            if self.is_visible("ultimate", search_context=search_context):
                self.log("Combat HUD returned. Resuming melee loop.")
                self._callbacks.status("MELEE LOOP", "#16a34a")
                if self.config.get("combat_settings", {}).get("smart_combat_enabled", True):
                    melee_result = self._combat_loop()
                else:
                    melee_result = self.auto_punch()
                if melee_result == "post_match":
                    self.handle_post_match()
                    return
                elif melee_result == "spectating":
                    continue
                return

            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                if time.time() - self.last_leave_click_time > 60:
                    mode = self.config.get("match_mode", "quick")
                    self.log(f"Return to Lobby detected in {mode} mode during spectate.")
                    self.last_leave_click_time = time.time()
                    if mode == "quick":
                        self.safe_find_and_click("return_to_lobby_alone")

            if time.time() - start_wait > 300:
                if not last_leave_logged:
                    self.log("Spectate timeout. Attempting to return to lobby.")
                    last_leave_logged = True
                self.handle_post_match()
                return
            self.sleep(1.0)

    def random_move(self) -> str:
        mode = self.config.get("match_mode", "full")
        keys = self.config.get("keys", {})
        forward = keys.get("forward", "w")
        backward = keys.get("backward", "s")
        left = keys.get("left", "a")
        right = keys.get("right", "d")
        active_window = self.config.get("movement_duration", 300)
        max_match_time = max(active_window + 300, 1080)
        start_game_time = time.time()
        last_log_time = 0

        while self.is_running() and time.time() - start_game_time < max_match_time:
            search_context = self.build_search_context()
            if self.is_visible("ultimate", search_context=search_context):
                self.log("Combat HUD detected during movement. Switching to melee loop.")
                self._callbacks.status("MELEE LOOP", "#16a34a")
                if self.config.get("combat_settings", {}).get("smart_combat_enabled", True):
                    melee_result = self._combat_loop()
                else:
                    melee_result = self.auto_punch()
                if melee_result == "post_match":
                    self.handle_post_match()
                return melee_result

            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                if time.time() - self.last_leave_click_time > 60:
                    if mode == "quick":
                        self.log("Quick mode: Return to Lobby during movement.")
                        self.last_leave_click_time = time.time()
                        self.safe_find_and_click("return_to_lobby_alone")
                self.handle_post_match()
                return "post_match"

            moves = [(forward, 0.4), (backward, 0.4), (left, 0.4), (right, 0.4)]
            move_key, move_dur = random.choice(moves)
            pydirectinput.keyDown(move_key)
            self.sleep(move_dur)
            pydirectinput.keyUp(move_key)
            self.sleep(random.uniform(0.1, 0.4))
            self.consecutive_return_prompt_scans = 0

        self.handle_post_match()
        return "post_match"

    def auto_punch(self) -> str:
        region = self._callbacks.get_search_region()
        if region is None:
            self.log("Cannot get window region for auto-punch.", is_error=True)
            return "post_match"
        p1 = self.resolve_coordinate("pos_1")
        p2 = self.resolve_coordinate("pos_2")
        if p1 is None or p2 is None:
            self.log("Combat coordinates not configured. Abort auto-punch.", is_error=True)
            return "post_match"
        keys = self.config.get("keys", {})
        menu_key = keys.get("menu", "m")
        slot1_key = keys.get("slot_1", "1")
        pydirectinput.press(menu_key)
        self.sleep(0.3)
        pydirectinput.press(slot1_key)
        self.sleep(0.3)
        cx1 = region["left"] + p1[0]
        cy1 = region["top"] + p1[1]
        cx2 = region["left"] + p2[0]
        cy2 = region["top"] + p2[1]
        human_click(cx1, cy1, self.is_running, offset=2, move=True)
        self.sleep(0.3)
        human_click(cx2, cy2, self.is_running, offset=2, move=True)
        self.sleep(0.3)
        start_wait = time.time()
        while self.is_running() and time.time() - start_wait < 30:
            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                return "post_match"
            if self.is_visible("ultimate"):
                return "spectating"
            self.sleep(1.0)
        return "post_match"

    def handle_post_match(self):
        self.log("Post-match phase started.")
        self._callbacks.status("POST MATCH", "#7c3aed")
        notification_sent = False
        start_wait = time.time()

        while self.is_running() and time.time() - start_wait < 120:
            search_context = self.build_search_context()
            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                if time.time() - self.last_leave_click_time > 60:
                    mode = self.config.get("match_mode", "full")
                    self.log(f"Return to Lobby detected in {mode} mode.")
                    self.last_leave_click_time = time.time()
                    self.safe_find_and_click("return_to_lobby_alone")
                    if mode == "quick":
                        self.log("Quick mode: waiting for post-match notification.")
                        while self.is_running() and time.time() - start_wait < 120:
                            sc = self.build_search_context()
                            if self.is_visible("ultimate"):
                                self.log("Ultimate detected after quick mode lobby. Match restarting.")
                                self._callbacks.status("MELEE LOOP", "#16a34a")
                                return
                            self.sleep(1.5)
                    self.sleep(2.0)
                    if not notification_sent:
                        elapsed = max(0, min(3600, int(time.time() - self.match_start_time)))
                        elapsed_text = f"{elapsed // 60}m {elapsed % 60}s"
                        message = f"Queue #{self._match_count} finished in {elapsed_text}"
                        screenshot_path = None
                        try:
                            region = self._callbacks.get_search_region()
                            if region and _MSS_AVAILABLE and mss:
                                with mss.mss() as sct:
                                    img = sct.grab(region)
                                    path = os.path.join(os.getcwd(), "screenshot_result.png")
                                    mss.mss().to_png(img.rgb, img.size, output=path)
                                    screenshot_path = path
                        except Exception:
                            pass
                        self._callbacks.discord(message, screenshot_path, "match_end")
                        notification_sent = True
                    self.match_active = False
                    self.log("Returned to lobby. Loop restarting.")
                    self._callbacks.status("IDLE", "#475569")
                    return
            self.sleep(1.0)

        self.log("Post-match timeout. Returning to lobby scan.")
        self.match_active = False

    def runtime_window_ready(self) -> bool:
        title = str(self.config.get("game_window_title", "")).strip()
        from src.utils.windows import find_window_by_title
        return bool(title and find_window_by_title(title))

    def get_combat_state(self) -> str:
        if self._combat_sm:
            return self._combat_sm.state_name
        return "IDLE"

    def get_combat_debug_info(self) -> dict:
        if self._combat_detector:
            return self._combat_detector.get_debug_info()
        return {}

    def reset_combat(self):
        if self._combat_detector:
            self._combat_detector.reset()
        if self._combat_sm:
            self._combat_sm.on_lobby()

    def invalidate_region_cache(self):
        self.cached_search_region = None


# ============================================================================
# Vision helpers (copied from src/core/vision.py — no app references)
# ============================================================================

def _get_mss_region():
    """Get the current game window region."""
    from src.utils.config import get_asset_capture_context
    ctx = get_asset_capture_context()
    if not ctx:
        return None
    monitors = mss.mss().monitors
    if not monitors:
        return None
    return ctx


def _locate_image(image_key: str, config: dict, confidence: float = None, region: dict = None) -> Optional[tuple]:
    """Locate an asset image in the capture region."""
    from src.core.vision import locate_image as _locate
    return _locate(image_key, config, confidence, region)


def _get_combat_detector(config: dict):
    """Get or create the combat signal detector."""
    from src.core.vision import get_combat_detector
    return get_combat_detector(config)


def _get_yolo_detector():
    """Get or create the YOLO detector singleton."""
    from src.core.vision import _get_yolo_detector as _get
    return _get()


# ============================================================================
# ZedsuCore — Public Entry Point
# ============================================================================

class ZedsuCore:
    """
    Pure bot logic engine for GPO BR.
    Callable as a library — no GUI, no Tkinter imports.
    Communicate with outer tiers via CoreCallbacks.
    """

    def __init__(self, callbacks: CoreCallbacks = None):
        self._callbacks = callbacks or NoOpCallbacks()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._engine = _ZedsuBotEngine(self._callbacks)
        self._match_count = 0

    def start(self):
        """Start the bot loop in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._pause_event.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ZedsuCore")
        self._thread.start()
        self._callbacks.log("ZedsuCore started", "info")

    def stop(self):
        """Signal stop and wait for the thread."""
        self._running = False
        self._stop_event.set()
        self._callbacks.log("ZedsuCore stopping...", "info")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._callbacks.log("ZedsuCore stopped", "info")

    def pause(self):
        """Pause the bot loop."""
        self._pause_event.clear()
        self._callbacks.log("ZedsuCore paused", "info")

    def resume(self):
        """Resume the bot loop."""
        self._pause_event.set()
        self._callbacks.log("ZedsuCore resumed", "info")

    def get_state(self) -> dict:
        """Return hierarchical state snapshot (per D-09b)."""
        return {
            "running": self._running,
            "combat_state": self._engine.get_combat_state(),
            "kills": self._engine._combat_sm._kill_count if self._engine._combat_sm else 0,
            "engaged_frames": self._engine._combat_sm._consecutive_engaged_frames if self._engine._combat_sm else 0,
            "match_count": self._match_count,
            "combat": self._engine.get_combat_debug_info(),
            "vision": {},
            "config": {},
        }

    def _run_loop(self):
        """Main loop — runs in daemon thread."""
        try:
            self._engine.bot_loop()
        except Exception as e:
            self._callbacks.log(f"ZedsuCore fatal error: {e}", "error")


def create_core(callbacks: CoreCallbacks = None) -> ZedsuCore:
    """Factory function — creates and returns a ZedsuCore instance."""
    return ZedsuCore(callbacks)


# ============================================================================
# Standalone test
# ============================================================================
if __name__ == "__main__":
    core = ZedsuCore(NoOpCallbacks())
    print("ZedsuCore instantiated OK — no GUI imports")
    print(f"State: {core.get_state()}")
