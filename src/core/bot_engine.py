from __future__ import annotations

import os
import random
import time
from enum import Enum, auto
from typing import Optional

import pyautogui
import pydirectinput

from src.core.controller import human_click, sleep_with_stop
from src.core.vision import (
    capture_search_context,
    find_and_click,
    get_combat_detector,
    is_image_visible,
    locate_image,
    _mss_capture_haystack,
    _normalize_region,
    _get_yolo_detector,
)
from src.utils.config import (
    CAPTURES_DIR,
    is_asset_custom,
    is_coordinate_ready,
    point_inside_window,
    resolve_coordinate,
    resolve_outcome_area,
)
from src.utils.windows import (
    bring_window_to_foreground,
    find_window_by_title,
    get_foreground_window_title,
    get_window_rect,
    is_window_active,
)
# Phase 12.5: Combat AI telemetry
from src.services.match_telemetry import MatchTelemetry, CombatTick, MatchSummary
# Phase 12.5: Target memory
from src.core.target_memory import TargetMemory, TargetDecision
# Phase 12.5: Combat situation model
from src.core.combat_situation import CombatSituationModel, CombatSituation, Intent
# Phase 12.5: Movement policy
from src.core.movement_policy import MovementPolicy, ScoredAction, MovementAction
from src.core.death_classifier import DeathClassifier, DeathClassification


# ============================================================
# PHASE 5: COMBAT STATE MACHINE
# ============================================================

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
        self._last_yolo_scan_time = 0  # Phase 8: throttle YOLO scans
        self._kill_milestone_sent: dict[int, bool] = {}  # Phase 12.4: per-match sent flags
        # Phase 12.5: Target memory reference (shared with engine)
        self._target_memory: Optional[TargetMemory] = None

        cfg = engine.app.config.get("combat_settings", {})
        self.disengage_timeout_sec = cfg.get("disengage_timeout_sec", 5.0)
        self.fleeing_hp_threshold = cfg.get("fleeing_hp_threshold", 0.25)
        self.dodge_chance = cfg.get("dodge_chance", 0.12)
        self.camera_scan_interval = cfg.get("camera_scan_interval", 0.5)
        self.kill_steal_resilient = cfg.get("kill_steal_resilient", True)
        # Phase 12.5: Share target memory with engine
        self._target_memory = engine._target_memory
        # Phase 12.5: Share situation model with engine
        self._situation_model: Optional[CombatSituationModel] = engine._situation_model
        # Phase 12.5: Movement policy reference
        self._movement_policy: Optional[MovementPolicy] = engine._movement_policy

    @property
    def state_name(self):
        return self.state.name

    def _transition_to(self, new_state):
        old = self.state
        self.state = new_state
        self._state_enter_time = time.time()
        self.engine.log(f"[COMBAT] {old.name} → {new_state.name}")
        self._consecutive_engaged_frames = 0
        self._consecutive_no_signal_frames = 0
        # Phase 12.5: Record state transition
        try:
            self.engine._telemetry.record_transition(old.name, new_state.name, "state_transition")
        except Exception:
            pass  # Non-fatal

    def update(self):
        """Called every combat tick (~500ms). Returns action dict for engine."""
        now = time.time()

        detector = self.engine._combat_detector
        if detector is None:
            return {"action": "idle"}

        signals = detector.scan_all_signals()

        enemy_nearby = signals.get("enemy_nearby", False)
        hit_confirmed = signals.get("hit_confirmed", False)
        in_combat = signals.get("in_combat", False)
        player_hp_low = signals.get("player_hp_low", False)
        kill_confirmed = signals.get("kill_confirmed", False)

        if kill_confirmed and not self._last_kill_detected:
            self._kill_count += 1
            self.engine.log(f"[COMBAT] Kill #{self._kill_count} confirmed!")

            # --- Phase 12.4: Kill milestone check ---
            try:
                from src.services.discord_event_service import (
                    should_dispatch,
                    dedupe_kill_milestone,
                )
                config = getattr(self.engine.app, 'config', {})
                if config and should_dispatch(config, "kill_milestone"):
                    thresholds = (
                        config.get("discord_events", {})
                        .get("kill_milestone_thresholds", [5, 10, 20])
                    )
                    for threshold in thresholds:
                        if self._kill_count >= threshold:
                            key = f"{getattr(self.engine.app, 'match_count', 0)}:{threshold}"
                            if not self._kill_milestone_sent.get(key):
                                self._kill_milestone_sent[key] = True
                                if self.engine and hasattr(self.engine, '_callbacks'):
                                    self.engine._callbacks.emit_event(
                                        "kill_milestone",
                                        title=f"Kill Milestone — #{threshold}",
                                        message=f"{self._kill_count} kills reached",
                                        match_id=getattr(self.engine.app, 'match_count', 0),
                                        kills=threshold,
                                        include_screenshot=False,
                                        metadata={},
                                    )
            except Exception:
                pass  # Kill milestone failures do not interrupt combat
            # --- end Phase 12.4 ---
        self._last_kill_detected = kill_confirmed

        self._last_incombat_time = now if in_combat else self._last_incombat_time

        if enemy_nearby or in_combat or hit_confirmed:
            self._consecutive_engaged_frames += 1
            self._consecutive_no_signal_frames = 0
        else:
            self._consecutive_no_signal_frames += 1
            self._consecutive_engaged_frames = max(0, self._consecutive_engaged_frames - 1)

        target = self._compute_target_state(
            enemy_nearby=enemy_nearby,
            in_combat=in_combat,
            hit_confirmed=hit_confirmed,
            player_hp_low=player_hp_low,
            now=now,
        )
        if target != self.state:
            self._transition_to(target)

        action = self._execute_state(signals, now)

        # Phase 12.5: Update target memory
        try:
            if self._target_memory is not None:
                screen_region = self.engine.get_search_region()
                screen_w = (screen_region[2] - screen_region[0]) if screen_region else 1920
                screen_h = (screen_region[3] - screen_region[1]) if screen_region else 1080
                screen_center = (screen_w / 2, screen_h / 2)
                screen_size = (screen_w, screen_h)

                # Get YOLO detections for target memory
                yolo_detections = []
                if self.state == CombatState.SCANNING:
                    yolo_result = self._yolo_scan_for_enemy()
                    if yolo_result and "raw_detections" in yolo_result:
                        yolo_detections = yolo_result.get("raw_detections", [])

                target_decision = self._target_memory.update(
                    yolo_detections=yolo_detections,
                    signals=signals,
                    screen_center=screen_center,
                    screen_size=screen_size,
                )

                action["target_memory"] = {
                    "has_target": target_decision.has_target,
                    "target_visible": target_decision.target_visible,
                    "confidence_ema": target_decision.confidence_ema,
                    "lost_ms": target_decision.lost_ms,
                    "center_error_x": target_decision.center_error_x,
                    "center_error_y": target_decision.center_error_y,
                    "reason": target_decision.reason,
                }
        except Exception:
            pass  # Non-fatal

        # Phase 12.5: Compute combat situation
        try:
            if self._situation_model is not None:
                # Re-call target_memory.update to get decision (idempotent)
                target_dec = self._target_memory.update(
                    yolo_detections=yolo_detections,
                    signals=signals,
                    screen_center=screen_center,
                    screen_size=screen_size,
                )
                track = self._target_memory.get_track()
                visible_count = 1 if track and track.bbox else 0
                if signals.get("enemy_nearby") or signals.get("in_combat"):
                    if visible_count == 0:
                        visible_count = 1

                situation = self._situation_model.assess(
                    signals=signals,
                    target_decision=target_dec,
                    visible_enemy_count=visible_count,
                    target_confidence_ema=getattr(target_dec, "confidence_ema", 0.0),
                )

                action["situation"] = {
                    "crowd_risk": situation.crowd_risk,
                    "death_risk": situation.death_risk,
                    "recommended_intent": situation.recommended_intent,
                    "target_loss_risk": situation.target_loss_risk,
                    "player_hp_low": situation.player_hp_low,
                    "visible_enemy_count": situation.visible_enemy_count,
                    "nearby_enemy_count": situation.nearby_enemy_count,
                    "crowd_risk_breakdown": situation.crowd_risk_breakdown,
                }
        except Exception:
            pass  # Non-fatal

        # Phase 12.5: Record combat tick
        try:
            target_info = action.get("target_memory", {})
            situation_info = action.get("situation", {})
            tick = CombatTick(
                ts=time.time(),
                t_match=time.time() - self.engine.match_start_time if self.engine.match_start_time else 0.0,
                match_id=getattr(self.engine.app, 'match_count', 0),
                state=self.state.name,
                action=action.get("action", "unknown"),
                signals=signals,
                target={
                    "visible": target_info.get("target_visible", False),
                    "confidence_ema": target_info.get("confidence_ema", 0.0),
                    "lost_ms": target_info.get("lost_ms", 0.0),
                    "center_error_x": target_info.get("center_error_x", 0.0),
                    "center_error_y": target_info.get("center_error_y", 0.0),
                },
                risk={
                    "crowd_risk": situation_info.get("crowd_risk", 0.0),
                    "death_risk": situation_info.get("death_risk", 0.0),
                    "target_loss_risk": situation_info.get("target_loss_risk", 0.0),
                    "visible_enemy_count": situation_info.get("visible_enemy_count", 0),
                },
                decision={
                    "intent": situation_info.get("recommended_intent", "scan"),
                    "target_memory": target_info,
                },
            )
            self.engine._telemetry.record_tick(tick)
        except Exception:
            pass  # Non-fatal

        return action

    def _compute_target_state(self, enemy_nearby, in_combat, hit_confirmed, player_hp_low, now):
        """Compute the target state based on signals."""
        s = self.state

        if self.engine.detect_spectating_state(search_context=self.engine.build_search_context()):
            return CombatState.SPECTATING

        if player_hp_low and s not in (CombatState.SPECTATING, CombatState.POST_MATCH, CombatState.IDLE):
            return CombatState.FLEEING

        if s == CombatState.FLEEING and not player_hp_low:
            return CombatState.SCANNING

        if enemy_nearby or in_combat or hit_confirmed:
            if s != CombatState.ENGAGED:
                return CombatState.ENGAGED
            return s

        no_signal_duration = now - max(self._last_enemy_detected, self._last_incombat_time)
        if no_signal_duration > self.disengage_timeout_sec and s == CombatState.ENGAGED:
            return CombatState.SCANNING

        # Phase 8: If in SCANNING and no pixel signals, try YOLO (D-26)
        if s == CombatState.SCANNING and not enemy_nearby and not in_combat:
            yolo_result = self._yolo_scan_for_enemy()
            if yolo_result:
                return CombatState.APPROACH  # D-15: YOLO sees enemy → APPROACH

        if s not in (CombatState.IDLE, CombatState.SPECTATING, CombatState.POST_MATCH):
            if not enemy_nearby and not in_combat:
                return CombatState.SCANNING

        return s

    def _execute_state(self, signals, now):
        """Execute behavior for current state. Returns action dict."""
        s = self.state

        if s == CombatState.SCANNING:
            self._last_enemy_detected = now
            return {
                "action": "scan",
                "scan_direction": self._scan_direction,
                "scan_timer": self._scan_timer,
                "enemy_nearby": signals.get("enemy_nearby", False),
                "in_combat": signals.get("in_combat", False),
                "green_ratio": signals.get("_green_ratio", 0.0),
            }

        elif s == CombatState.ENGAGED:
            return {
                "action": "attack",
                "enemy_nearby": signals.get("enemy_nearby", False),
                "in_combat": signals.get("in_combat", False),
                "hit_confirmed": signals.get("hit_confirmed", False),
                "dodge_chance": self.dodge_chance,
                "kill_steal_resilient": self.kill_steal_resilient,
                "enemy_green_ratio": signals.get("_green_ratio", 0.0),
            }

        elif s == CombatState.FLEEING:
            return {
                "action": "flee",
                "player_hp_ratio": signals.get("_player_green_ratio", 0.0),
            }

        elif s == CombatState.SPECTATING:
            return {"action": "spectate"}

        elif s == CombatState.POST_MATCH:
            return {"action": "post_match"}

        else:
            return {"action": "idle"}

    def on_match_start(self):
        """Called when a match starts."""
        self._transition_to(CombatState.SCANNING)
        self._kill_count = 0
        self._consecutive_engaged_frames = 0
        self._consecutive_no_signal_frames = 0
        self._kill_milestone_sent = {}  # Phase 12.4: reset per-match milestone flags
        if self.engine._combat_detector:
            self.engine._combat_detector.reset()

    def on_death(self):
        """Called when death is detected."""
        self._transition_to(CombatState.SPECTATING)
        # Phase 12.4: emit death event once (smart path — from FSM transition)
        try:
            self.engine._emit_death_event_once("combat_sm")
        except Exception:
            pass

    def on_results_screen(self):
        """Called when results screen detected."""
        self._transition_to(CombatState.POST_MATCH)

    def on_lobby(self):
        """Called when lobby is detected."""
        self._transition_to(CombatState.IDLE)

    def get_status(self):
        """For UI display."""
        return {
            "combat_state": self.state.name,
            "kills": self._kill_count,
            "engaged_frames": self._consecutive_engaged_frames,
        }

    # Phase 8: YOLO Enemy Detection (D-26, D-27)
    def _yolo_scan_for_enemy(self):
        """
        YOLO-based enemy detection for SCANNING state.
        Called when green HP bar signal is absent.
        Throttled to 1-2s intervals (D-14).
        Returns dict with enemy info or None.
        """
        now = time.time()
        # Throttle: only scan every 1.5 seconds (D-14)
        if now - self._last_yolo_scan_time < 1.5:
            return None
        self._last_yolo_scan_time = now

        try:
            import numpy as np
        except ImportError:
            return None

        # Get YOLO detector
        yolo_det = _get_yolo_detector()
        if not yolo_det.is_available():
            return None

        # Capture full window frame
        region = self.engine.get_search_region()
        if not region:
            return None

        normalized = _normalize_region(region)
        haystack_rgb, offset = _mss_capture_haystack(normalized)
        if haystack_rgb is None:
            return None

        haystack_bgr = haystack_rgb[:, :, ::-1]  # RGB -> BGR

        # Detect enemy_player class (class_id=8)
        detections = yolo_det.detect(haystack_bgr, class_ids=[8])
        if not detections:
            return None

        # D-27: Pick nearest to screen center
        best = self._select_nearest_to_center(detections, haystack_rgb.shape)
        _, conf, (x, y, w, h) = best

        return {
            "enemy_detected": True,
            "class_id": 8,
            "confidence": conf,
            "box": (x, y, w, h),
            "center_distance": self._center_distance((x, y, w, h), haystack_rgb.shape),
            "raw_detections": detections,  # Phase 12.5: for target memory
        }

    def _select_nearest_to_center(self, detections, image_shape):
        """Select detection closest to screen center (D-27)."""
        h, w = image_shape[:2]
        center_x, center_y = w / 2, h / 2
        best = None
        best_dist = float("inf")
        for det in detections:
            _, _, (x, y, bw, bh) = det
            cx = x + bw / 2
            cy = y + bh / 2
            dist = ((cx - center_x) ** 2 + (cy - center_y) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = det
        return best

    def _center_distance(self, box, image_shape):
        """Compute distance from detection center to screen center."""
        h, w = image_shape[:2]
        center_x, center_y = w / 2, h / 2
        x, y, bw, bh = box
        cx = x + bw / 2
        cy = y + bh / 2
        return ((cx - center_x) ** 2 + (cy - center_y) ** 2) ** 0.5


# ============================================================
# BOT ENGINE
# ============================================================

class BotEngine:
    def __init__(self, app):
        self.app = app
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
        self.consecutive_spectating_checks = 0
        self.match_active = False
        self.cached_search_region = None
        self.cached_search_region_time = 0
        self.visibility_cache = {}
        # Phase 12.4: Discord event system
        self._last_screenshot_region = None
        self._death_event_sent = False
        self._callbacks = getattr(app, '_callbacks', getattr(app, 'callbacks', None))

        # Phase 5: Combat state machine
        self._combat_detector = None
        self._combat_sm = None
        self._combat_tick_interval = 0.5
        self._last_combat_tick = 0

        # Phase 12.5: Combat AI telemetry singleton
        self._telemetry = MatchTelemetry.get_instance(getattr(app, 'config', {}))
        # Phase 12.5: Target memory
        self._target_memory = TargetMemory(getattr(app, 'config', {}))
        # Phase 12.5: Combat situation model
        self._situation_model = CombatSituationModel(getattr(app, 'config', {}))
        # Phase 12.5: Movement policy
        self._movement_policy = MovementPolicy(getattr(app, 'config', {}))
        # Phase 12.5: Death classifier
        self._death_classifier = DeathClassifier(getattr(app, 'config', {}))

    def start(self):
        self.stop_requested = False
        self.consecutive_return_prompt_scans = 0
        self.consecutive_melee_failures = 0
        self.consecutive_spectating_checks = 0
        self.match_wait_transition_logged = False
        self.invalidate_runtime_caches(clear_region=True)
        # Phase 5: reset combat system
        self._combat_detector = None
        self._combat_sm = None
        self._last_combat_tick = 0

    def stop(self):
        self.stop_requested = True

    def _ensure_combat_system(self):
        """Lazily initialize combat detector and state machine."""
        if self._combat_detector is None:
            self._combat_detector = get_combat_detector(self.app.config)
        if self._combat_sm is None:
            self._combat_sm = CombatStateMachine(self)

    def _combat_tick(self):
        """
        One tick of the combat state machine (~500ms interval).
        This replaces the linear auto_punch() loop when smart_combat_enabled=True.
        """
        now = time.time()
        if now - self._last_combat_tick < self._combat_tick_interval:
            return
        self._last_combat_tick = now
        self._ensure_combat_system()

        action = self._combat_sm.update()

        if action["action"] == "scan":
            self._scan_for_enemies(action)
        elif action["action"] == "attack":
            self._execute_engaged_combat(action)
        elif action["action"] == "flee":
            self._execute_fleeing(action)
        elif action["action"] == "spectate":
            result = self.handle_spectating_phase()
            if result in ("lobby", "resume"):
                if result == "lobby":
                    self._combat_sm.on_lobby()
        elif action["action"] == "post_match":
            self.handle_post_match()
            self._combat_sm.on_lobby()
        elif action["action"] == "idle":
            pass

    def _scan_for_enemies(self, action):
        """SCANNING state behavior: camera rotation + light movement."""
        cfg = self.app.config
        keys_cfg = cfg.get("keys", {})
        move_keys = [
            keys_cfg.get("forward", "w"),
            keys_cfg.get("left", "a"),
            keys_cfg.get("backward", "s"),
            keys_cfg.get("right", "d"),
        ]

        scan_key = move_keys[1] if action["scan_direction"] > 0 else move_keys[3]
        pydirectinput.keyDown(scan_key)
        self.sleep(0.3)
        pydirectinput.keyUp(scan_key)
        self._combat_sm._scan_direction *= -1

        if random.random() < 0.3:
            pydirectinput.keyDown(move_keys[0])
            self.sleep(random.uniform(0.2, 0.5))
            pydirectinput.keyUp(move_keys[0])

        self._check_combat_exit_conditions()

    def _execute_engaged_combat(self, action):
        """ENGAGED state behavior: M1 spam + dodge."""
        cfg = self.app.config
        keys_cfg = cfg.get("keys", {})
        slot1_key = keys_cfg.get("slot_1", "1")

        if not self.ensure_melee_equipped(slot1_key):
            pydirectinput.press(slot1_key)
            self.sleep(0.3)

        for _ in range(5):
            if not self.is_running():
                return
            pydirectinput.click()
            self.last_punch_time = time.time()
            if not self.sleep(random.uniform(0.06, 0.11)):
                return

            exit_result = self._check_combat_exit_conditions()
            if exit_result:
                return

        self.grant_provisional_melee(18)

        if random.random() < action.get("dodge_chance", 0.12):
            backward = keys_cfg.get("backward", "s")
            pydirectinput.keyDown(backward)
            self.sleep(random.uniform(0.15, 0.3))
            pydirectinput.keyUp(backward)

        self.perform_dynamic_combat_movement(
            [keys_cfg.get("forward", "w"),
             keys_cfg.get("left", "a"),
             keys_cfg.get("backward", "s"),
             keys_cfg.get("right", "d")],
            bursts=random.randint(1, 2),
            situation=action.get("situation"),
            target_decision=action.get("target_memory"),
        )

    def _execute_fleeing(self, action):
        """FLEEING state behavior: evasive movement."""
        cfg = self.app.config
        keys_cfg = cfg.get("keys", {})
        backward = keys_cfg.get("backward", "s")

        pydirectinput.keyDown(backward)
        self.sleep(random.uniform(0.3, 0.6))
        pydirectinput.keyUp(backward)

        strafe = random.choice([keys_cfg.get("left", "a"), keys_cfg.get("right", "d")])
        pydirectinput.keyDown(strafe)
        self.sleep(random.uniform(0.2, 0.4))
        pydirectinput.keyUp(strafe)

        if self._combat_detector:
            signals = self._combat_detector.scan_all_signals()
            if not signals.get("player_hp_low", False):
                self.log("[COMBAT] HP recovered, returning to scan mode.")

    def _check_combat_exit_conditions(self):
        """Check for spectating/results/lobby during combat. Returns truthy if should exit."""
        search_context = self.build_search_context()

        if self.is_visible("open", search_context=search_context) or \
           self.is_visible("continue", search_context=search_context):
            self.log("[COMBAT] Results screen detected.")
            self._combat_sm.on_results_screen()
            self.handle_post_match()
            return True

        if self.detect_spectating_state(search_context=search_context):
            self.log("[COMBAT] Spectating detected.")
            self._combat_sm.on_death()
            return True

        return False

    def is_running(self):
        return self.app.is_running and not self.stop_requested

    def log(self, msg, is_error=False):
        self.app.log(msg, is_error=is_error)

    def sleep(self, seconds):
        return sleep_with_stop(seconds, self.is_running)

    def invalidate_runtime_caches(self, clear_region=False):
        self.visibility_cache.clear()
        if clear_region:
            self.cached_search_region = None
            self.cached_search_region_time = 0

    def provisional_melee_active(self):
        return self.provisional_melee_until > time.time()

    def grant_provisional_melee(self, seconds):
        self.provisional_melee_until = max(self.provisional_melee_until, time.time() + max(0, seconds))

    def recent_melee_confirmation_active(self, max_age=20.0):
        return self.last_melee_confirm_time > 0 and (time.time() - self.last_melee_confirm_time) <= max_age

    def mark_match_active(self, reason=None):
        if self.match_active:
            return False
        self._death_event_sent = False  # Phase 12.4: reset death guard on new match

        self.match_active = True
        self.match_wait_transition_logged = False
        self.match_start_time = time.time()
        self.app.match_count += 1
        self.app.update_match_count()

        # Phase 12.5: Start match telemetry
        try:
            self._telemetry.start_match(self.app.match_count)
        except Exception:
            pass  # Non-fatal

        # Phase 12.5: Reset target memory on new match
        try:
            self._target_memory.reset()
        except Exception:
            pass

        # Phase 12.5: Reset movement policy on new match
        try:
            self._movement_policy.reset()
        except Exception:
            pass  # Non-fatal

        if reason:
            self.log(f"Match #{self.app.match_count} started ({reason}).")
        else:
            self.log(f"Match #{self.app.match_count} started.")
        return True

    def _emit_death_event_once(self, source: str):
        """
        Emit a single death Discord event, guarded against double-send.
        Smart path calls from CombatStateMachine.on_death() → _combat_sm.on_death() wrapper.
        Non-smart path calls from handle_spectating_phase() entry.

        Args:
            source: "combat_sm" or "spectating_phase" — for logging only
        """
        if self._death_event_sent:
            return
        self._death_event_sent = True
        try:
            if hasattr(self, '_callbacks') and self._callbacks:
                raw_region = self.get_search_region()
                region = None
                if raw_region:
                    region = {
                        "left": raw_region[0],
                        "top": raw_region[1],
                        "right": raw_region[2],
                        "bottom": raw_region[3],
                    }

                # Phase 12.5: Classify death reason from telemetry
                death_reason = "unknown"
                death_confidence = 0.0
                death_meta = {}
                try:
                    if hasattr(self, '_death_classifier') and self._death_classifier:
                        last_ticks = self._telemetry.get_last_ticks(20)
                        if last_ticks:
                            cls_result = self._death_classifier.classify(last_ticks)
                            death_reason = cls_result.reason
                            death_confidence = cls_result.confidence
                            death_meta = {
                                "death_reason": cls_result.reason,
                                "death_confidence": cls_result.confidence,
                                "last_state": cls_result.last_state,
                                "crowd_risk": cls_result.crowd_risk,
                                "visible_enemy_count": cls_result.visible_enemy_count,
                                "target_lost_ms": cls_result.target_lost_ms,
                                "player_hp_low": cls_result.player_hp_low,
                                "classification_breakdown": cls_result.metadata,
                            }
                        else:
                            death_meta = {"death_reason": "unknown", "no_telemetry": True}
                    else:
                        death_meta = {"death_reason": "unknown", "classifier_disabled": True}
                except Exception:
                    death_meta = {"death_reason": "unknown", "classifier_error": True}

                self._callbacks.emit_event(
                    "death",
                    title=f"You Died — Match #{self.app.match_count}",
                    message="You died",
                    match_id=self.app.match_count,
                    include_screenshot=True,
                    metadata={
                        "screenshot_region": region,
                        "death_reason": death_reason,
                        "death_confidence": death_confidence,
                        **death_meta,
                    },
                )
                self.log(f"[COMBAT] Death event dispatched (source: {source}, reason: {death_reason}).")
        except Exception:
            pass  # Death event failures do not interrupt spectating watch

    def clear_match_active(self):
        self.match_active = False
        self._death_event_sent = False  # Phase 12.4: reset death guard
        self.match_wait_transition_logged = False
        self.consecutive_return_prompt_scans = 0
        self.consecutive_melee_failures = 0
        self.consecutive_spectating_checks = 0
        self.provisional_melee_until = 0

    def ensure_game_focused(self):
        if not self.app.config.get("window_focus_required", True):
            return True

        title = str(self.app.config.get("game_window_title", "")).strip()
        if not title:
            return False

        if is_window_active(title):
            return True

        if self.app.config.get("auto_focus_window", True) and bring_window_to_foreground(title):
            self.invalidate_runtime_caches(clear_region=True)
            self.log(f"Focused game window: {title}")
            self.app.update_status("FOCUSING GAME", "#0f766e")
            return self.sleep(0.6)

        if time.time() - self.last_focus_log_time > 10:
            self.log(f"Waiting for game window: {title}", is_error=True)
            self.last_focus_log_time = time.time()
        return False

    def get_search_region(self, force_refresh=False):
        title = str(self.app.config.get("game_window_title", "")).strip()
        if not title:
            return None
        now = time.time()
        if (
            not force_refresh
            and self.cached_search_region is not None
            and (now - self.cached_search_region_time) <= 0.35
        ):
            return self.cached_search_region

        region = get_window_rect(title)
        self.cached_search_region = region
        self.cached_search_region_time = now
        return region

    def build_search_context(self, force_refresh=False):
        return capture_search_context(self.get_search_region(force_refresh=force_refresh))

    def is_visible(self, image_key, confidence=None, cache_ttl=0.2, search_context=None):
        region = search_context.get("region") if search_context else self.get_search_region()
        cache_key = (image_key, round(confidence or -1.0, 3), region)
        now = time.time()
        cached = self.visibility_cache.get(cache_key)
        if cached and (now - cached["time"]) <= cache_ttl:
            return cached["value"]

        visible = is_image_visible(
            image_key,
            self.app.config,
            confidence=confidence,
            region=region,
            search_context=search_context,
        )
        self.visibility_cache[cache_key] = {"time": now, "value": visible}
        return visible

    def safe_find_and_click(self, image_key, clicks=1, confidence=None, search_context=None):
        if not self.ensure_game_focused():
            return False
        self.invalidate_runtime_caches()
        active_context = search_context or self.build_search_context()
        clicked = find_and_click(
            image_key,
            self.app.config,
            self.is_running,
            self.log,
            clicks=clicks,
            region=active_context.get("region"),
            confidence=confidence,
            search_context=active_context,
        )
        if clicked:
            self.invalidate_runtime_caches()
        return clicked

    def tap_current_position(self):
        if not self.is_running():
            return False
        pydirectinput.mouseDown()
        if not self.sleep(0.08):
            pydirectinput.mouseUp()
            return False
        pydirectinput.mouseUp()
        self.invalidate_runtime_caches()
        return True

    def click_saved_coordinate(self, key, label, clicks=1, move_first=True, offset=2, pause=0.1):
        current_window = self.get_search_region(force_refresh=True)
        point = resolve_coordinate(self.app.config, key, window_rect=current_window)
        if not is_coordinate_ready(point):
            self.log(f"{label} coordinate is not configured.", is_error=True)
            return False

        if current_window and not point_inside_window(point, current_window, margin=1):
            self.log(
                f"{label} resolved outside the current Roblox window. Re-pick this coordinate for the current client size.",
                is_error=True,
            )
            return False

        for index in range(clicks):
            if not human_click(point[0], point[1], self.is_running, move=move_first if index == 0 else False, offset=offset):
                return False
            self.invalidate_runtime_caches()
            if index < clicks - 1 and not self.sleep(pause):
                return False
        return True

    def capture_game_frame(self):
        region = self.get_search_region()
        if not region:
            return None

        left, top, right, bottom = region
        try:
            return pyautogui.screenshot(region=(left, top, right - left, bottom - top))
        except Exception as exc:
            self.log(f"Could not capture the Roblox window for combat checks: {exc}", is_error=True)
            return None

    def _threshold_ratio(self, image, lower=None, upper=None):
        histogram = image.convert("L").histogram()
        total = max(1, sum(histogram))
        start = 0 if lower is None else max(0, int(lower))
        end = 255 if upper is None else min(255, int(upper))
        if end < start:
            return 0.0
        return sum(histogram[start : end + 1]) / total

    def is_slot_one_selected(self):
        frame = self.capture_game_frame()
        if frame is None:
            return False

        width, height = frame.size
        if width < 400 or height < 300:
            return False

        melee_panel = frame.crop(
            (
                int(width * 0.84),
                int(height * 0.56),
                int(width * 0.995),
                int(height * 0.93),
            )
        )
        slot_box = frame.crop(
            (
                int(width * 0.455),
                int(height * 0.88),
                int(width * 0.505),
                int(height * 0.982),
            )
        )

        panel_bright = self._threshold_ratio(melee_panel, lower=212)
        panel_dark = self._threshold_ratio(melee_panel, upper=92)
        slot_bright = self._threshold_ratio(slot_box, lower=220)
        slot_dark = self._threshold_ratio(slot_box, upper=90)

        return (panel_bright >= 0.055 and panel_dark >= 0.28) or (slot_bright >= 0.16 and slot_dark >= 0.18)

    def get_combat_indicator_regions(self):
        region = self.get_search_region()
        if not region:
            return []

        left, top, right, bottom = region
        width = right - left
        height = bottom - top
        return [
            (
                left + int(width * 0.42),
                top + int(height * 0.78),
                left + int(width * 0.58),
                top + int(height * 0.995),
            ),
            (
                left + int(width * 0.78),
                top + int(height * 0.5),
                right,
                top + int(height * 0.96),
            ),
            (
                left + int(width * 0.35),
                top + int(height * 0.46),
                right,
                bottom,
            ),
        ]

    def locate_combat_ready_asset(self):
        if not is_asset_custom(self.app.config, "combat_ready"):
            return None

        confidence = max(0.6, float(self.app.config.get("confidence", 0.8)) - 0.08)
        for region in self.get_combat_indicator_regions():
            result = locate_image("combat_ready", self.app.config, confidence=confidence, region=region)
            if result:
                return result

        full_region = self.get_search_region()
        should_run_wide_scan = (
            full_region is not None
            and (self.combat_asset_miss_count >= 2 or not self.recent_melee_confirmation_active(max_age=6.0))
            and (time.time() - self.last_wide_combat_scan_time) >= 1.2
        )
        if should_run_wide_scan:
            self.last_wide_combat_scan_time = time.time()
            return locate_image(
                "combat_ready",
                self.app.config,
                confidence=max(0.55, confidence - 0.05),
                region=full_region,
            )
        return None

    def is_melee_equipped(self):
        if is_asset_custom(self.app.config, "combat_ready"):
            if self.locate_combat_ready_asset():
                self.last_melee_confirm_time = time.time()
                self.combat_asset_miss_count = 0
                self.consecutive_melee_failures = 0
                self.consecutive_spectating_checks = 0
                self.grant_provisional_melee(30)
                return True
            self.combat_asset_miss_count += 1
            if self.recent_melee_confirmation_active(max_age=20.0):
                return True
            if time.time() - self.last_combat_asset_log_time > 18:
                self.log(
                    "Combat asset was not visible long enough. Falling back to slot heuristics for melee confirmation.",
                )
                self.last_combat_asset_log_time = time.time()

        slot_ready = self.is_slot_one_selected()
        if slot_ready:
            self.last_melee_confirm_time = time.time()
            self.combat_asset_miss_count = 0
            self.consecutive_melee_failures = 0
            self.consecutive_spectating_checks = 0
            self.grant_provisional_melee(30)
        return slot_ready

    def ensure_melee_equipped(self, slot1_key):
        if self.is_melee_equipped():
            return True

        if self.provisional_melee_active():
            return True

        for attempt in range(4):
            pydirectinput.press(slot1_key)
            if time.time() - self.last_slot_warning_time > 14:
                self.log("Melee was not confirmed. Pressing slot 1 and checking combat state again.")
                self.last_slot_warning_time = time.time()
            if not self.sleep(0.22 + (attempt * 0.06)):
                return False
            if random.random() < 0.65:
                pydirectinput.moveRel(random.randint(-48, 48), random.randint(-10, 10))
            if self.is_melee_equipped():
                self.log("Melee equip confirmed.")
                return True

        self.consecutive_melee_failures += 1
        if self.consecutive_melee_failures >= 3:
            pydirectinput.press(slot1_key)
            self.grant_provisional_melee(18)
            self.consecutive_melee_failures = 0
            if time.time() - self.last_melee_fallback_log_time > 20:
                self.log("Melee confirmation stayed flaky. Running a guarded fallback cycle after re-pressing slot 1.")
                self.last_melee_fallback_log_time = time.time()
            return True

        if time.time() - self.last_slot_warning_time > 14:
            self.log("Could not confirm melee equip yet. Continuing dynamic movement and retrying.", is_error=True)
            self.last_slot_warning_time = time.time()
        return False

    def lobby_visible(self, search_context=None):
        return (
            self.is_visible("change", search_context=search_context)
            or self.is_visible("solo_mode", search_context=search_context)
            or self.is_visible("br_mode", search_context=search_context)
        )

    def detect_spectating_state(self, search_context=None):
        if self.is_visible("open", search_context=search_context) or self.is_visible(
            "continue",
            search_context=search_context,
        ):
            self.consecutive_spectating_checks = 0
            return False

        if not self.is_visible("return_to_lobby_alone", confidence=0.7, search_context=search_context):
            self.consecutive_spectating_checks = 0
            return False

        if self.is_visible("ultimate", search_context=search_context):
            self.consecutive_spectating_checks = 0
            return False

        if self.recent_melee_confirmation_active(max_age=2.0) and self.combat_asset_miss_count == 0:
            self.consecutive_spectating_checks = 0
            return False

        self.consecutive_spectating_checks += 1
        return self.consecutive_spectating_checks >= 3

    def handle_spectating_phase(self):
        self.consecutive_spectating_checks = 0
        self.consecutive_melee_failures = 0
        self.provisional_melee_until = 0
        # Phase 12.4: emit death event once (non-smart path — from spectating detection)
        try:
            self._emit_death_event_once("spectating_phase")
        except Exception:
            pass
        self.log("Spectating detected during melee loop. Switching to post-death watch.")
        self.app.update_status("SPECTATING", "#7c3aed")

        start_wait = time.time()
        quick_leave_logged = False
        full_mode_wait_logged = False

        while self.is_running():
            if not self.ensure_game_focused():
                if not self.sleep(0.5):
                    return False
                continue

            search_context = self.build_search_context()
            open_visible = self.is_visible("open", search_context=search_context)
            continue_visible = self.is_visible("continue", search_context=search_context)
            if open_visible or continue_visible:
                self.log("Results detected while spectating. Switching to post-match handling.")
                return "post_match"

            if self.is_visible("ultimate", search_context=search_context):
                self.log("Combat HUD returned. Resuming melee loop.")
                self.app.update_status("MELEE LOOP", "#16a34a")
                return "resume"

            leave_visible = self.is_visible(
                "return_to_lobby_alone",
                confidence=0.7,
                search_context=search_context,
            )
            if leave_visible:
                if self.app.config.get("match_mode") == "quick":
                    if not quick_leave_logged:
                        self.log("Quick mode is leaving early from spectating via Return To Lobby.")
                        quick_leave_logged = True
                    if time.time() - self.last_leave_click_time > 4:
                        if self.safe_find_and_click(
                            "return_to_lobby_alone",
                            clicks=2,
                            confidence=0.7,
                            search_context=search_context,
                        ):
                            self.last_leave_click_time = time.time()
                            if not self.sleep(2.2):
                                return False
                elif not full_mode_wait_logged:
                    self.log("Return To Lobby is visible while spectating. Full mode will keep waiting for the real result screen.")
                    full_mode_wait_logged = True

            if self.lobby_visible(search_context=search_context):
                self.clear_match_active()
                self.log("Lobby detected after spectating. Returning to queue scan.")
                return "lobby"

            if time.time() - start_wait > 1500:
                self.log("Spectating watch timed out after 25 minutes. Returning to lobby scan.", is_error=True)
                self.clear_match_active()
                return "lobby"

            if not self.sleep(1.0):
                return False

        return False

    def resolve_combat_loop_status(self, status):
        if status == "spectating":
            return self.handle_spectating_phase()
        return status

    def handle_combat_exit_conditions(self, search_context=None):
        open_visible = self.is_visible("open", search_context=search_context)
        continue_visible = self.is_visible("continue", search_context=search_context)
        if open_visible or continue_visible:
            self.log("Results detected during melee loop.")
            return "post_match"

        if self.detect_spectating_state(search_context=search_context):
            return "spectating"

        leave_visible = self.is_visible(
            "return_to_lobby_alone",
            confidence=0.7,
            search_context=search_context,
        )
        if leave_visible and time.time() - self.last_leave_click_time > 60:
            if self.app.config.get("match_mode") == "quick":
                if self.safe_find_and_click(
                    "return_to_lobby_alone",
                    clicks=2,
                    confidence=0.7,
                    search_context=search_context,
                ):
                    self.log("Quick mode leave confirmed.")
                    self.last_leave_click_time = time.time()
                    return "post_match"
            elif self.tap_current_position():
                self.last_leave_click_time = time.time()

        return None

    def handle_match_presence_fallback(self):
        self.consecutive_return_prompt_scans += 1
        if self.consecutive_return_prompt_scans < 3:
            return False

        if time.time() - self.last_match_hint_log_time > 25:
            self.log(
                "Return-to-lobby stayed visible without lobby assets. Treating this as an in-match fallback state.",
            )
            self.last_match_hint_log_time = time.time()

        self.mark_match_active("fallback state")
        self.app.update_status("IN MATCH (FALLBACK)", "#16a34a")
        movement_result = self.random_move()
        self.consecutive_return_prompt_scans = 0
        if movement_result == "post_match":
            self.handle_post_match()
        return True

    def hold_movement_keys(self, keys, duration):
        active_keys = [key for key in keys if key]
        for key in active_keys:
            pydirectinput.keyDown(key)

        try:
            return self.sleep(duration)
        finally:
            for key in reversed(active_keys):
                pydirectinput.keyUp(key)

    def perform_dynamic_combat_movement(self, move_keys, bursts=None, situation=None, target_decision=None):
        """
        Phase 12.5: Replaced body with scored movement policy.
        Old random pattern selection is preserved as fallback.

        Args:
            move_keys: [forward, left, backward, right] — kept for fallback
            bursts: number of movement steps (default random 1-3)
            situation: CombatSituation from situation model
            target_decision: TargetDecision from target memory
        """
        steps = bursts if bursts is not None else random.randint(1, 3)
        last_action = None

        for _ in range(steps):
            if not self.is_running():
                return None

            # Phase 12.5: Scored movement selection
            try:
                if self._movement_policy is not None and situation is not None:
                    intent = situation.get("recommended_intent", "engage") if isinstance(situation, dict) else getattr(situation, "recommended_intent", "engage")

                    class _SitStub:
                        def __init__(self, d):
                            self.crowd_risk = d.get("crowd_risk", 0.0)
                            self.player_hp_low = d.get("player_hp_low", False)
                            self.death_risk = d.get("death_risk", 0.0)
                            self.visible_enemy_count = d.get("visible_enemy_count", 0)
                            self.nearby_enemy_count = d.get("nearby_enemy_count", 0)
                    sit = _SitStub(situation) if isinstance(situation, dict) else situation

                    action = self._movement_policy.choose_action(
                        intent=intent,
                        situation=sit,
                        target_decision=target_decision,
                        last_action=last_action,
                    )

                    if action.name == "hold_position":
                        if not self.sleep(random.uniform(*action.duration_range)):
                            return False
                        last_action = "hold_position"
                        continue

                    actual_keys = []
                    for k in action.keys:
                        if k == "w" and len(move_keys) > 0:
                            actual_keys.append(move_keys[0])
                        elif k == "a" and len(move_keys) > 1:
                            actual_keys.append(move_keys[1])
                        elif k == "s" and len(move_keys) > 2:
                            actual_keys.append(move_keys[2])
                        elif k == "d" and len(move_keys) > 3:
                            actual_keys.append(move_keys[3])

                    if actual_keys:
                        if not self.hold_movement_keys(actual_keys, random.uniform(*action.duration_range)):
                            return False

                    err_x = getattr(target_decision, "center_error_x", 0.0) if target_decision else 0.0
                    if "camera_correct" in action.name:
                        if "left" in action.name:
                            pydirectinput.moveRel(-abs(int(err_x * 0.5)) if err_x < 0 else -50, 0)
                        elif "right" in action.name:
                            pydirectinput.moveRel(abs(int(err_x * 0.5)) if err_x > 0 else 50, 0)

                    if "scan" in action.name:
                        if "left" in action.name:
                            pydirectinput.moveRel(-60, random.randint(-10, 10))
                        elif "right" in action.name:
                            pydirectinput.moveRel(60, random.randint(-10, 10))

                    last_action = action.name

                else:
                    if not self._execute_random_movement_fallback(move_keys):
                        return False
                    last_action = None
            except Exception:
                if not self._execute_random_movement_fallback(move_keys):
                    return False
                last_action = None

            status = self.handle_combat_exit_conditions(search_context=self.build_search_context())
            if status:
                return status

            if not self.sleep(random.uniform(0.05, 0.12)):
                return False

        return None

    def _execute_random_movement_fallback(self, move_keys) -> bool:
        """Fallback to old pure-random movement behavior."""
        if len(move_keys) < 4:
            return True
        forward, left, backward, right = move_keys[:4]
        patterns = [
            ([left], (0.11, 0.2)),
            ([right], (0.11, 0.2)),
            ([forward, left], (0.14, 0.24)),
            ([forward, right], (0.14, 0.24)),
            ([backward, left], (0.1, 0.18)),
            ([backward, right], (0.1, 0.18)),
            ([forward], (0.16, 0.28)),
        ]
        pattern_keys, duration_range = random.choice(patterns)
        return bool(self.hold_movement_keys(pattern_keys, random.uniform(*duration_range)))

    def bot_loop(self):
        self.start()
        self.log("Bot loop started.")

        while self.is_running():
            try:
                if not self.ensure_game_focused():
                    self.app.update_status("WAITING FOR GAME WINDOW", "#b45309")
                    self.sleep(1.0)
                    continue

                self.app.update_status("SCANNING LOBBY", "#2563eb")
                search_context = self.build_search_context()

                return_prompt_visible = self.handle_lobby_return_prompt(search_context=search_context)
                if return_prompt_visible == "quick_leave":
                    self.sleep(0.4)
                    continue

                if self.is_visible("ultimate", search_context=search_context):
                    self.log("Ultimate bar detected. Starting combat.")
                    self.on_match_detected()
                    self.app.update_status("MELEE LOOP", "#16a34a")
                    self.consecutive_return_prompt_scans = 0

                    if self.app.config.get("combat_settings", {}).get("smart_combat_enabled", True):
                        self._ensure_combat_system()
                        self._combat_sm.on_match_start()
                        # Phase 12.4: emit combat_start event
                        try:
                            if hasattr(self, '_callbacks') and self._callbacks:
                                self._callbacks.emit_event(
                                    "combat_start",
                                    title=f"Combat Started — #{self.app.match_count}",
                                    message="Combat started",
                                    match_id=self.app.match_count,
                                    include_screenshot=False,
                                    metadata={},
                                )
                        except Exception:
                            pass  # Combat start event failures do not interrupt combat loop
                        self._last_combat_tick = 0
                        while self.is_running():
                            sc = self.build_search_context()
                            if self.is_visible("open", search_context=sc) or \
                               self.is_visible("continue", search_context=sc):
                                self.log("Results detected from combat loop.")
                                self.handle_post_match()
                                break
                            if self.detect_spectating_state(search_context=sc):
                                self._combat_sm.on_death()
                                result = self.handle_spectating_phase()
                                if result == "lobby":
                                    self._combat_sm.on_lobby()
                                    break
                                elif result == "resume":
                                    self._combat_sm.on_match_start()
                                    continue
                            self._combat_tick()
                            if not self.sleep(0.05):
                                break
                        self._combat_sm.on_lobby()
                    else:
                        combat_result = self.auto_punch()
                        if combat_result == "post_match":
                            self.handle_post_match()
                    continue

                open_visible = self.is_visible("open", search_context=search_context)
                continue_visible = self.is_visible("continue", search_context=search_context)
                if open_visible or continue_visible:
                    self.log("Result screen detected from main loop.")
                    self.consecutive_return_prompt_scans = 0
                    self.handle_post_match()
                    continue

                if self.is_visible("solo_mode", search_context=search_context):
                    if self.safe_find_and_click("solo_mode", search_context=search_context):
                        self.log("Solo queue confirmed.")
                        self.consecutive_return_prompt_scans = 0
                        self.handle_match_waiting()
                        continue
                elif self.is_visible("br_mode", search_context=search_context):
                    self.consecutive_return_prompt_scans = 0
                    self.safe_find_and_click("br_mode", search_context=search_context)
                else:
                    if self.safe_find_and_click("change", search_context=search_context):
                        self.consecutive_return_prompt_scans = 0
                    elif return_prompt_visible == "visible":
                        if self.handle_match_presence_fallback():
                            continue
                    elif not self.is_running():
                        break
                    elif time.time() - self.last_no_detection_log_time > 15:
                        foreground = get_foreground_window_title() or "[unknown]"
                        self.log(
                            "No lobby assets detected in the current Roblox window. "
                            f"Foreground window: {foreground}. "
                            "If the game was resized or another app is covering it, template matching will fail.",
                            is_error=True,
                        )
                        self.last_no_detection_log_time = time.time()

                self.sleep(self.app.config.get("scan_interval", 1.5))
            except Exception as exc:
                self.log(f"Loop error: {exc}", is_error=True)
                # Phase 12.4: emit bot_error event (sanitized in service layer)
                try:
                    if hasattr(self, '_callbacks') and self._callbacks:
                        self._callbacks.emit_event(
                            "bot_error",
                            title="Bot Error",
                            message=str(exc),
                            source="bot_engine.bot_loop",
                            match_id=getattr(self.app, 'match_count', None),
                            include_screenshot=True,
                            metadata={"screenshot_region": None},  # None = full screen capture
                        )
                except Exception:
                    pass
                self.sleep(2.0)

        self.app.update_status("IDLE", "#475569")
        self.log("Bot loop stopped.")

    def on_match_detected(self):
        self.mark_match_active()

    def handle_lobby_return_prompt(self, search_context=None):
        if not self.is_visible("return_to_lobby_alone", confidence=0.7, search_context=search_context):
            self.consecutive_return_prompt_scans = 0
            return None

        if time.time() - self.last_lobby_log_time > 45:
            mode = self.app.config.get("match_mode", "full").upper()
            self.log(f"Return to lobby button detected in {mode} mode.")
            self.last_lobby_log_time = time.time()

        if self.app.config.get("match_mode") == "quick":
            if self.safe_find_and_click(
                "return_to_lobby_alone",
                clicks=2,
                confidence=0.7,
                search_context=search_context,
            ):
                self.last_leave_click_time = time.time()
                self.clear_match_active()
                return "quick_leave"
        elif time.time() - self.last_leave_click_time > 60:
            if self.tap_current_position():
                self.last_leave_click_time = time.time()
        return "visible"

    def handle_match_waiting(self):
        self.log("Waiting for match to fully load.")
        self.app.update_status("WAITING FOR MATCH", "#d97706")
        start_wait = time.time()
        last_log_time = 0
        soft_timeout = 480
        hard_timeout = 900

        while self.is_running() and time.time() - start_wait < hard_timeout:
            elapsed = int(time.time() - start_wait)
            log_interval = 30 if elapsed < 300 else 45 if elapsed < soft_timeout else 60
            if elapsed - last_log_time >= log_interval:
                self.log(f"Still waiting for match confirmation... {elapsed}s")
                last_log_time = elapsed

            if elapsed >= soft_timeout and not self.match_wait_transition_logged:
                self.match_wait_transition_logged = True
                self.log("Match load is taking longer than usual. Staying in transition watch mode instead of dropping back early.")
                self.app.update_status("MATCH TRANSITION WATCH", "#b45309")

            search_context = self.build_search_context()
            if self.is_visible("ultimate", search_context=search_context):
                self.log("Ultimate detected in match wait phase.")
                self.match_wait_transition_logged = False
                self.on_match_detected()
                self.app.update_status("MELEE LOOP", "#16a34a")
                combat_result = self.auto_punch()
                if combat_result == "post_match":
                    self.handle_post_match()
                return

            if self.is_visible("return_to_lobby_alone", confidence=0.7, search_context=search_context):
                self.log("Return to lobby detected in match wait phase. Switching to movement mode.")
                self.match_wait_transition_logged = False
                self.mark_match_active("movement fallback")
                self.app.update_status("IN MATCH", "#16a34a")
                if self.random_move() == "post_match":
                    self.handle_post_match()
                return

            if self.is_visible("change", search_context=search_context):
                self.match_wait_transition_logged = False
                self.clear_match_active()
                self.log("Lobby detected again. Queue likely cancelled.")
                return

            self.sleep(0.5 if elapsed < soft_timeout else 0.8)

        self.match_wait_transition_logged = False
        self.log("Match wait timed out after extended transition watch. Returning to lobby scan.", is_error=True)

    def random_move(self):
        mode = self.app.config.get("match_mode", "full")
        keys_cfg = self.app.config.get("keys", {})
        move_keys = [
            keys_cfg.get("forward", "w"),
            keys_cfg.get("left", "a"),
            keys_cfg.get("backward", "s"),
            keys_cfg.get("right", "d"),
        ]

        active_movement_window = self.app.config.get("movement_duration", 300)
        max_match_time = max(active_movement_window + 300, 1080)
        start_game_time = time.time()
        low_activity_logged = False

        self.log(f"Movement phase started in {mode.upper()} mode.")

        while self.is_running():
            elapsed = time.time() - start_game_time
            active_roaming = elapsed <= active_movement_window

            if not low_activity_logged and not active_roaming:
                self.log("Active movement window finished. Switching to light keep-alive movement.")
                low_activity_logged = True

            key = random.choice(move_keys)
            hold_duration = random.uniform(0.25, 0.65) if active_roaming else random.uniform(0.08, 0.2)
            pydirectinput.keyDown(key)
            if not self.sleep(hold_duration):
                pydirectinput.keyUp(key)
                return
            pydirectinput.keyUp(key)

            search_context = self.build_search_context()
            if self.is_visible("ultimate", search_context=search_context):
                self.log("Ultimate detected during movement. Switching to melee loop.")
                self.app.update_status("MELEE LOOP", "#16a34a")
                combat_result = self.auto_punch()
                if combat_result == "post_match":
                    return "post_match"
                return None

            if self.is_visible("open", search_context=search_context) or self.is_visible(
                "continue",
                search_context=search_context,
            ):
                self.log("Result buttons detected. Ending movement phase.")
                return "post_match"

            if self.is_visible("return_to_lobby_alone", confidence=0.7, search_context=search_context):
                if time.time() - self.last_leave_click_time > 60:
                    if self.app.config.get("match_mode") == "quick":
                        if self.safe_find_and_click(
                            "return_to_lobby_alone",
                            clicks=2,
                            confidence=0.7,
                            search_context=search_context,
                        ):
                            self.log("Quick mode leave confirmed.")
                            self.last_leave_click_time = time.time()
                            return "post_match"
                    elif self.tap_current_position():
                        self.last_leave_click_time = time.time()

            if random.random() < (0.25 if active_roaming else 0.08):
                pydirectinput.moveRel(random.randint(-120, 120), random.randint(-12, 12))

            if elapsed > max_match_time:
                self.log("Reached maximum match time. Breaking into post-match scan.", is_error=True)
                return "post_match"

            self.sleep(random.uniform(0.45, 1.2) if active_roaming else random.uniform(1.0, 2.0))

        return None

    def auto_punch(self):
        pos1 = resolve_coordinate(self.app.config, "pos_1", window_rect=self.get_search_region(force_refresh=True))
        pos2 = resolve_coordinate(self.app.config, "pos_2", window_rect=self.get_search_region())
        if not is_coordinate_ready(pos1) or not is_coordinate_ready(pos2):
            self.log("Combat setup coordinates are not configured. Aborting auto-punch.", is_error=True)
            return False

        keys_cfg = self.app.config.get("keys", {})
        menu_key = keys_cfg.get("menu", "m")
        slot1_key = keys_cfg.get("slot_1", "1")
        move_keys = [
            keys_cfg.get("forward", "w"),
            keys_cfg.get("left", "a"),
            keys_cfg.get("backward", "s"),
            keys_cfg.get("right", "d"),
        ]

        self.log("Ultimate bar confirmed. Preparing melee stat setup.")
        # Phase 12.4: emit combat_start for non-smart path
        try:
            if hasattr(self, '_callbacks') and self._callbacks:
                self._callbacks.emit_event(
                    "combat_start",
                    title=f"Combat Started — #{self.app.match_count}",
                    message="Combat started",
                    match_id=self.app.match_count,
                    include_screenshot=False,
                    metadata={},
                )
        except Exception:
            pass
        if not self.sleep(1.2):
            return False

        if not self.ensure_game_focused():
            return False

        pydirectinput.press(menu_key)
        if not self.sleep(0.9):
            return False

        if not self.click_saved_coordinate("pos_1", "Statistics icon", clicks=1, move_first=True, offset=4, pause=0.0):
            return False
        self.log("Statistics menu opened.")
        if not self.sleep(1.0):
            return False

        self.log("Applying 15 melee upgrades.")
        if not self.click_saved_coordinate("pos_2", "Melee upgrade button", clicks=15, move_first=True, offset=2, pause=0.08):
            return False

        pydirectinput.press(menu_key)
        if not self.sleep(0.6):
            return False
        pydirectinput.press(slot1_key)
        if not self.sleep(0.3):
            return False
        self.grant_provisional_melee(75)
        if not self.ensure_melee_equipped(slot1_key):
            self.log("Could not confirm melee equip before the first combat cycle. The loop will keep retrying.", is_error=True)

        self.log("Melee loop active: confirm equip, attack 5 hits, dynamic move, repeat.")

        while self.is_running():
            if not self.ensure_game_focused():
                if not self.sleep(0.35):
                    return False
                continue

            status = self.resolve_combat_loop_status(
                self.handle_combat_exit_conditions(search_context=self.build_search_context())
            )
            if status == "post_match":
                return "post_match"
            if status == "lobby":
                return "lobby"
            if status is False:
                return False

            if not self.ensure_melee_equipped(slot1_key):
                recovery_result = self.resolve_combat_loop_status(
                    self.perform_dynamic_combat_movement(move_keys, bursts=1)
                )
                if recovery_result == "post_match":
                    return "post_match"
                if recovery_result == "lobby":
                    return "lobby"
                if recovery_result is False:
                    return False
                if not self.sleep(0.2):
                    return False
                continue

            for _ in range(5):
                status = self.resolve_combat_loop_status(
                    self.handle_combat_exit_conditions(search_context=self.build_search_context())
                )
                if status == "post_match":
                    return "post_match"
                if status == "lobby":
                    return "lobby"
                if status is False:
                    return False

                pydirectinput.click()
                self.last_punch_time = time.time()
                if not self.sleep(random.uniform(0.06, 0.11)):
                    return False

            self.grant_provisional_melee(18)
            movement_result = self.resolve_combat_loop_status(self.perform_dynamic_combat_movement(move_keys))
            if movement_result == "post_match":
                return "post_match"
            if movement_result == "lobby":
                return "lobby"
            if movement_result is False:
                return False

        return False

    def capture_result_screenshot(self):
        screenshot_path = os.path.join(CAPTURES_DIR, "match_finish.png")
        try:
            full_screenshot = pyautogui.screenshot()
            area = resolve_outcome_area(self.app.config, window_rect=self.get_search_region())
            if area:
                left, top, right, bottom = area
                cropped = full_screenshot.crop((left, top, right, bottom))
                cropped.save(screenshot_path)
            else:
                full_screenshot.save(screenshot_path)
            return screenshot_path
        except Exception as exc:
            self.log(f"Screenshot error: {exc}", is_error=True)
            return None

    def handle_post_match(self):
        self.log("Post-match phase started.")
        self.app.update_status("POST MATCH", "#7c3aed")
        notification_sent = False
        start_wait = time.time()
        last_progress_time = time.time()

        if self.match_start_time == 0:
            self.match_start_time = time.time() - 60

        while self.is_running():
            if time.time() - start_wait > 300:
                self.log("Post-match timed out after 5 minutes.")
                self.clear_match_active()
                return

            if time.time() - last_progress_time > 120:
                self.log("No post-match progress for 2 minutes. Returning to lobby scan.", is_error=True)
                self.clear_match_active()
                return

            search_context = self.build_search_context()
            open_visible = self.is_visible("open", search_context=search_context)
            continue_visible = self.is_visible("continue", search_context=search_context)
            leave_visible = self.is_visible(
                "return_to_lobby_alone",
                confidence=0.7,
                search_context=search_context,
            )

            if open_visible or continue_visible or leave_visible:
                last_progress_time = time.time()

            if (continue_visible or leave_visible) and not notification_sent:
                # Phase 12.4: reset kill dedupe for this match
                from src.services.discord_event_service import reset_kill_dedupe
                reset_kill_dedupe(self.app.match_count)

                # Capture screenshot region for emit
                raw_region = self.get_search_region()
                if raw_region:
                    self._last_screenshot_region = {
                        "left": raw_region[0],
                        "top": raw_region[1],
                        "right": raw_region[2],
                        "bottom": raw_region[3],
                    }

                elapsed = max(0, min(3600, int(time.time() - self.match_start_time)))
                elapsed_text = f"{elapsed // 60}m {elapsed % 60}s"
                kills = 0
                if self._combat_sm is not None:
                    kills = self._combat_sm._kill_count

                # emit_event replaces legacy callbacks.discord() — non-blocking via worker queue
                self._callbacks.emit_event(
                    "match_end",
                    title=f"Match Complete — #{self.app.match_count}",
                    message=f"{elapsed_text} | {kills} kills",
                    match_id=self.app.match_count,
                    kills=kills,
                    include_screenshot=True,
                    metadata={"screenshot_region": self._last_screenshot_region},
                )
                self.log(f"Discord match_end event dispatched (match #{self.app.match_count}).")
                notification_sent = True

                # Phase 12.5: Finish telemetry + death classification
                death_reason = "unknown"
                try:
                    if hasattr(self, '_death_classifier') and self._death_classifier and hasattr(self, '_telemetry'):
                        last_ticks = self._telemetry.get_last_ticks(20)
                        if last_ticks:
                            cls_result = self._death_classifier.classify(last_ticks)
                            death_reason = cls_result.reason
                except Exception:
                    pass

                try:
                    summary = MatchSummary(
                        match_id=self.app.match_count,
                        started_at=self.match_start_time,
                        ended_at=time.time(),
                        duration_sec=max(0, min(3600, int(time.time() - self.match_start_time))),
                        kills=kills,
                        death_reason=death_reason,
                        exit_state=self._combat_sm.state.name if self._combat_sm else "unknown",
                    )
                    self._telemetry.finish_match(summary)
                except Exception:
                    pass  # Non-fatal

                self.sleep(0.8)

            if open_visible:
                if self.safe_find_and_click("open", clicks=2, search_context=search_context):
                    self.sleep(1.5)
                    continue

            if continue_visible:
                if self.safe_find_and_click("continue", clicks=2, search_context=search_context):
                    self.log("Continue clicked. Returning to lobby.")
                    self.sleep(2.5)
                    self.clear_match_active()
                    return

            if leave_visible:
                self.log("Attempting to return to lobby.")
                if self.safe_find_and_click(
                    "return_to_lobby_alone",
                    clicks=3,
                    confidence=0.7,
                    search_context=search_context,
                ):
                    self.sleep(2.5)
                    self.clear_match_active()
                    return

            self.sleep(1.5)

    def runtime_window_ready(self):
        title = str(self.app.config.get("game_window_title", "")).strip()
        return bool(title and find_window_by_title(title))

    def get_combat_status(self):
        """Return combat state for UI display."""
        if self._combat_sm is None:
            return {"combat_state": "IDLE", "kills": 0, "engaged_frames": 0}
        return self._combat_sm.get_status()
