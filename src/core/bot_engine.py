import os
import random
import time

import pyautogui
import pydirectinput

from src.core.controller import human_click, sleep_with_stop
from src.core.vision import find_and_click, is_image_visible, locate_image
from src.utils.config import (
    CAPTURES_DIR,
    is_asset_custom,
    is_coordinate_ready,
    point_inside_window,
    resolve_coordinate,
    resolve_outcome_area,
)
from src.utils.discord import send_discord
from src.utils.windows import (
    bring_window_to_foreground,
    find_window_by_title,
    get_foreground_window_title,
    get_window_rect,
    is_window_active,
)


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

    def start(self):
        self.stop_requested = False
        self.consecutive_return_prompt_scans = 0
        self.consecutive_melee_failures = 0
        self.consecutive_spectating_checks = 0
        self.match_wait_transition_logged = False
        self.invalidate_runtime_caches(clear_region=True)

    def stop(self):
        self.stop_requested = True

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

        self.match_active = True
        self.match_wait_transition_logged = False
        self.match_start_time = time.time()
        self.app.match_count += 1
        self.app.update_match_count()

        if reason:
            self.log(f"Match #{self.app.match_count} started ({reason}).")
        else:
            self.log(f"Match #{self.app.match_count} started.")
        return True

    def clear_match_active(self):
        self.match_active = False
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

    def is_visible(self, image_key, confidence=None, cache_ttl=0.2):
        region = self.get_search_region()
        cache_key = (image_key, round(confidence or -1.0, 3), region)
        now = time.time()
        cached = self.visibility_cache.get(cache_key)
        if cached and (now - cached["time"]) <= cache_ttl:
            return cached["value"]

        visible = is_image_visible(image_key, self.app.config, confidence=confidence, region=region)
        self.visibility_cache[cache_key] = {"time": now, "value": visible}
        return visible

    def safe_find_and_click(self, image_key, clicks=1, confidence=None):
        if not self.ensure_game_focused():
            return False
        self.invalidate_runtime_caches()
        clicked = find_and_click(
            image_key,
            self.app.config,
            self.is_running,
            self.log,
            clicks=clicks,
            region=self.get_search_region(),
            confidence=confidence,
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

    def lobby_visible(self):
        return self.is_visible("change") or self.is_visible("solo_mode") or self.is_visible("br_mode")

    def detect_spectating_state(self):
        if self.is_visible("open") or self.is_visible("continue"):
            self.consecutive_spectating_checks = 0
            return False

        if not self.is_visible("return_to_lobby_alone", confidence=0.7):
            self.consecutive_spectating_checks = 0
            return False

        if self.is_visible("ultimate"):
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

            if self.is_visible("open") or self.is_visible("continue"):
                self.log("Results detected while spectating. Switching to post-match handling.")
                return "post_match"

            if self.is_visible("ultimate"):
                self.log("Combat HUD returned. Resuming melee loop.")
                self.app.update_status("MELEE LOOP", "#16a34a")
                return "resume"

            leave_visible = self.is_visible("return_to_lobby_alone", confidence=0.7)
            if leave_visible:
                if self.app.config.get("match_mode") == "quick":
                    if not quick_leave_logged:
                        self.log("Quick mode is leaving early from spectating via Return To Lobby.")
                        quick_leave_logged = True
                    if time.time() - self.last_leave_click_time > 4:
                        if self.safe_find_and_click("return_to_lobby_alone", clicks=2, confidence=0.7):
                            self.last_leave_click_time = time.time()
                            if not self.sleep(2.2):
                                return False
                elif not full_mode_wait_logged:
                    self.log("Return To Lobby is visible while spectating. Full mode will keep waiting for the real result screen.")
                    full_mode_wait_logged = True

            if self.lobby_visible():
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

    def handle_combat_exit_conditions(self):
        if self.is_visible("open") or self.is_visible("continue"):
            self.log("Results detected during melee loop.")
            return "post_match"

        if self.detect_spectating_state():
            return "spectating"

        leave_visible = self.is_visible("return_to_lobby_alone", confidence=0.7)
        if leave_visible and time.time() - self.last_leave_click_time > 60:
            if self.app.config.get("match_mode") == "quick":
                if self.safe_find_and_click("return_to_lobby_alone", clicks=2, confidence=0.7):
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

    def perform_dynamic_combat_movement(self, move_keys, bursts=None):
        if len(move_keys) < 4:
            return None

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

        steps = bursts if bursts is not None else random.randint(1, 3)
        for _ in range(steps):
            pattern_keys, duration_range = random.choice(patterns)
            if not self.hold_movement_keys(pattern_keys, random.uniform(*duration_range)):
                return False

            if random.random() < 0.85:
                pydirectinput.moveRel(random.randint(-165, 165), random.randint(-24, 24))

            status = self.handle_combat_exit_conditions()
            if status:
                return status

            if not self.sleep(random.uniform(0.05, 0.12)):
                return False

        return None

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

                return_prompt_visible = self.handle_lobby_return_prompt()
                if return_prompt_visible == "quick_leave":
                    self.sleep(0.4)
                    continue

                if self.is_visible("ultimate"):
                    self.log("Ultimate bar detected. Starting melee loop.")
                    self.on_match_detected()
                    self.app.update_status("MELEE LOOP", "#16a34a")
                    self.consecutive_return_prompt_scans = 0
                    combat_result = self.auto_punch()
                    if combat_result == "post_match":
                        self.handle_post_match()
                    continue

                if self.is_visible("open") or self.is_visible("continue"):
                    self.log("Result screen detected from main loop.")
                    self.consecutive_return_prompt_scans = 0
                    self.handle_post_match()
                    continue

                if self.is_visible("solo_mode"):
                    if self.safe_find_and_click("solo_mode"):
                        self.log("Solo queue confirmed.")
                        self.consecutive_return_prompt_scans = 0
                        self.handle_match_waiting()
                        continue
                elif self.is_visible("br_mode"):
                    self.consecutive_return_prompt_scans = 0
                    self.safe_find_and_click("br_mode")
                else:
                    if self.safe_find_and_click("change"):
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
                self.sleep(2.0)

        self.app.update_status("IDLE", "#475569")
        self.log("Bot loop stopped.")

    def on_match_detected(self):
        self.mark_match_active()

    def handle_lobby_return_prompt(self):
        if not self.is_visible("return_to_lobby_alone", confidence=0.7):
            self.consecutive_return_prompt_scans = 0
            return None

        if time.time() - self.last_lobby_log_time > 45:
            mode = self.app.config.get("match_mode", "full").upper()
            self.log(f"Return to lobby button detected in {mode} mode.")
            self.last_lobby_log_time = time.time()

        if self.app.config.get("match_mode") == "quick":
            if self.safe_find_and_click("return_to_lobby_alone", clicks=2, confidence=0.7):
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

            if self.is_visible("ultimate"):
                self.log("Ultimate detected in match wait phase.")
                self.match_wait_transition_logged = False
                self.on_match_detected()
                self.app.update_status("MELEE LOOP", "#16a34a")
                combat_result = self.auto_punch()
                if combat_result == "post_match":
                    self.handle_post_match()
                return

            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                self.log("Return to lobby detected in match wait phase. Switching to movement mode.")
                self.match_wait_transition_logged = False
                self.mark_match_active("movement fallback")
                self.app.update_status("IN MATCH", "#16a34a")
                if self.random_move() == "post_match":
                    self.handle_post_match()
                return

            if self.is_visible("change"):
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

            if self.is_visible("ultimate"):
                self.log("Ultimate detected during movement. Switching to melee loop.")
                self.app.update_status("MELEE LOOP", "#16a34a")
                combat_result = self.auto_punch()
                if combat_result == "post_match":
                    return "post_match"
                return None

            if self.is_visible("open") or self.is_visible("continue"):
                self.log("Result buttons detected. Ending movement phase.")
                return "post_match"

            if self.is_visible("return_to_lobby_alone", confidence=0.7):
                if time.time() - self.last_leave_click_time > 60:
                    if self.app.config.get("match_mode") == "quick":
                        if self.safe_find_and_click("return_to_lobby_alone", clicks=2, confidence=0.7):
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

            status = self.resolve_combat_loop_status(self.handle_combat_exit_conditions())
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
                status = self.resolve_combat_loop_status(self.handle_combat_exit_conditions())
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

            open_visible = self.is_visible("open")
            continue_visible = self.is_visible("continue")
            leave_visible = self.is_visible("return_to_lobby_alone", confidence=0.7)

            if open_visible or continue_visible or leave_visible:
                last_progress_time = time.time()

            if (continue_visible or leave_visible) and not notification_sent:
                screenshot_path = self.capture_result_screenshot()
                elapsed = max(0, min(3600, int(time.time() - self.match_start_time)))
                elapsed_text = f"{elapsed // 60}m {elapsed % 60}s"
                message = f"Queue #{self.app.match_count} finished in {elapsed_text}"
                status_code = send_discord(self.app.config.get("discord_webhook"), message, file_path=screenshot_path)
                if status_code:
                    self.log(f"Discord notification sent ({status_code}).")
                else:
                    self.log("Discord notification skipped or failed.")
                notification_sent = True
                self.sleep(0.8)

            if open_visible:
                if self.safe_find_and_click("open", clicks=2):
                    self.sleep(1.5)
                    continue

            if continue_visible:
                if self.safe_find_and_click("continue", clicks=2):
                    self.log("Continue clicked. Returning to lobby.")
                    self.sleep(2.5)
                    self.clear_match_active()
                    return

            if leave_visible:
                self.log("Attempting to return to lobby.")
                if self.safe_find_and_click("return_to_lobby_alone", clicks=3, confidence=0.7):
                    self.sleep(2.5)
                    self.clear_match_active()
                    return

            self.sleep(1.5)

    def runtime_window_ready(self):
        title = str(self.app.config.get("game_window_title", "")).strip()
        return bool(title and find_window_by_title(title))
