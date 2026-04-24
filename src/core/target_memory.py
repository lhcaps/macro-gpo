"""
Target Memory — Phase 12.5.

Tracks a single target across frames using an EMA confidence filter and
grace period for short visual loss. Prevents target thrashing in multi-enemy fights.

Design:
- Single active track: only one target is tracked at a time
- EMA smoothing: confidence and distance are exponentially smoothed to reduce jitter
- Grace period: if target is lost for < target_lost_grace_sec, keep pursuing
- Switch penalty: hard penalty for switching to a new target to prevent thrashing
- Hit confirm anchoring: if hit_confirm is recent, stay on current target even if not visually confirmed
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TargetTrack:
    """A single target being tracked over time."""
    bbox: Optional[tuple[int, int, int, int]] = None  # (x, y, w, h) or None if not visible
    confidence_ema: float = 0.0                        # Exponential moving average of confidence
    last_seen_ts: float = 0.0                         # time.time() of last visible frame
    first_seen_ts: float = 0.0                        # time.time() of first detection
    lost_frames: int = 0                               # Consecutive frames with no detection
    hit_confirm_count: int = 0                         # Frames with hit_confirm signal
    center_distance_ema: float = float("inf")         # EMA of center distance in pixels
    source: str = "none"                              # yolo | hsv | hit_confirm | inferred
    track_id: int = 0                                 # Unique track ID for debugging


@dataclass
class TargetDecision:
    """The result of a target memory update — what the bot should do."""
    has_target: bool                                   # We have a tracked target (visible or in grace)
    target_visible: bool                               # Target is currently in frame
    should_pursue: bool                               # Should chase the target
    should_scan: bool                                 # Should do camera scan instead
    should_reposition: bool                           # Should reposition (not about target)
    center_error_x: float = 0.0                       # Pixel error from screen center (target)
    center_error_y: float = 0.0
    reason: str = ""                                  # Human-readable reason for decision
    confidence_ema: float = 0.0                       # Smoothed confidence of current target
    lost_ms: float = 0.0                             # Milliseconds since last visible detection


# ---------------------------------------------------------------------------
# TargetMemory
# ---------------------------------------------------------------------------

class TargetMemory:
    """
    Tracks the active combat target across frames with EMA smoothing.

    Usage:
        mem = TargetMemory(config)
        decision = mem.update(
            yolo_detections=[...],    # Raw YOLO detections this frame (may be empty)
            signals={"hit_confirmed": True, ...},
            screen_center=(960, 540),
            screen_size=(1920, 1080),
        )
        # decision.target_visible, decision.should_pursue, etc.
    """

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("combat_ai", {})
        self._enabled = cfg.get("target_memory_enabled", True)
        self._grace_sec = cfg.get("target_lost_grace_sec", 2.0)
        self._switch_penalty = cfg.get("target_switch_penalty", 0.35)
        self._deadzone_px = cfg.get("target_center_deadzone_px", 90)
        self._ema_alpha = 0.3   # Smoothing factor for EMA

        self._track: Optional[TargetTrack] = None
        self._track_counter = 0
        self._last_hit_confirm_ts: float = 0.0
        self._last_update_ts: float = time.time()

    def reset(self) -> None:
        """Reset all target memory. Call on new match."""
        self._track = None
        self._last_hit_confirm_ts = 0.0

    def update(
        self,
        yolo_detections: list,
        signals: dict,
        screen_center: tuple[float, float],
        screen_size: tuple[int, int],
    ) -> TargetDecision:
        """
        Update target memory with new frame data.

        Args:
            yolo_detections: List of (class_id, confidence, (x, y, w, h)) from YOLO
            signals: CombatSignalDetector output dict
            screen_center: (cx, cy) in pixels
            screen_size: (width, height) in pixels

        Returns:
            TargetDecision with has_target, should_pursue, should_scan, etc.
        """
        if not self._enabled:
            return self._default_decision("disabled")

        now = time.time()
        hit_confirmed = signals.get("hit_confirmed", False)
        in_combat = signals.get("in_combat", False)
        enemy_nearby = signals.get("enemy_nearby", False)

        if hit_confirmed:
            self._last_hit_confirm_ts = now

        # Filter to enemy_player detections (class_id == 8)
        enemy_dets = [d for d in yolo_detections if len(d) >= 3 and d[0] == 8]

        # Update EMA alpha based on detection stability
        alpha = self._ema_alpha

        if enemy_dets:
            # Pick best detection (highest confidence, nearest to center as tiebreaker)
            best = self._pick_best_detection(enemy_dets, screen_center, screen_size)
            class_id, conf, (x, y, w, h) = best

            det_center_x = x + w / 2
            det_center_y = y + h / 2
            cx, cy = screen_center
            center_dist = ((det_center_x - cx) ** 2 + (det_center_y - cy) ** 2) ** 0.5
            center_err_x = det_center_x - cx
            center_err_y = det_center_y - cy

            if self._track is None:
                # No existing track — start new one
                self._track_counter += 1
                self._track = TargetTrack(
                    bbox=(x, y, w, h),
                    confidence_ema=conf,
                    last_seen_ts=now,
                    first_seen_ts=now,
                    lost_frames=0,
                    hit_confirm_count=1 if hit_confirmed else 0,
                    center_distance_ema=center_dist,
                    source="yolo",
                    track_id=self._track_counter,
                )
            else:
                # Check if this detection matches the existing track
                if self._bbox_overlaps((x, y, w, h), self._track.bbox):
                    # Same target — update EMA
                    self._track.bbox = (x, y, w, h)
                    self._track.confidence_ema = (
                        alpha * conf + (1 - alpha) * self._track.confidence_ema
                    )
                    self._track.center_distance_ema = (
                        alpha * center_dist + (1 - alpha) * self._track.center_distance_ema
                    )
                    self._track.last_seen_ts = now
                    self._track.lost_frames = 0
                    if hit_confirmed:
                        self._track.hit_confirm_count += 1
                else:
                    # Different target — switch penalty applies
                    switch_score = conf - self._switch_penalty
                    if switch_score > self._track.confidence_ema * 0.8:
                        # Switch target
                        self._track_counter += 1
                        self._track = TargetTrack(
                            bbox=(x, y, w, h),
                            confidence_ema=conf,
                            last_seen_ts=now,
                            first_seen_ts=now,
                            lost_frames=0,
                            hit_confirm_count=1 if hit_confirmed else 0,
                            center_distance_ema=center_dist,
                            source="yolo",
                            track_id=self._track_counter,
                        )

        # Update lost state
        if self._track is not None and enemy_dets:
            pass  # Already updated above
        elif self._track is not None:
            self._track.lost_frames += 1
            self._track.bbox = None  # No longer visible

        self._last_update_ts = now

        # Build decision
        return self._build_decision(signals, screen_center, now)

    def _pick_best_detection(
        self,
        detections: list,
        screen_center: tuple[float, float],
        screen_size: tuple[int, int],
    ) -> tuple:
        """Pick the best detection: highest confidence, nearest to center as tiebreaker."""
        cx, cy = screen_center
        best = None
        best_score = -1.0
        for det in detections:
            class_id, conf, (x, y, w, h) = det
            center_x = x + w / 2
            center_y = y + h / 2
            dist = ((center_x - cx) ** 2 + (center_y - cy) ** 2) ** 0.5
            score = conf * 1000 - dist  # Confidence primary, distance secondary
            if score > best_score:
                best_score = score
                best = det
        return best

    def _bbox_overlaps(
        self,
        bbox1: Optional[tuple],
        bbox2: Optional[tuple],
        iou_threshold: float = 0.3,
    ) -> bool:
        """Check if two bboxes overlap sufficiently (IoU-style check)."""
        if bbox1 is None or bbox2 is None:
            return False
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        # Simple overlap check
        ox1 = max(x1, x2)
        oy1 = max(y1, y2)
        ox2 = min(x1 + w1, x2 + w2)
        oy2 = min(y1 + h1, y2 + h2)
        if ox1 >= ox2 or oy1 >= oy2:
            return False
        overlap_area = (ox2 - ox1) * (oy2 - oy1)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - overlap_area
        if union <= 0:
            return False
        iou = overlap_area / union
        return iou >= iou_threshold

    def _build_decision(
        self,
        signals: dict,
        screen_center: tuple[float, float],
        now: float,
    ) -> TargetDecision:
        """Build a TargetDecision from current track state."""
        if self._track is None:
            return self._default_decision("no_track")

        lost_sec = now - self._track.last_seen_ts
        hit_confirm_recent = (now - self._last_hit_confirm_ts) < 3.0

        if lost_sec > self._grace_sec and not hit_confirm_recent:
            # Target lost beyond grace period — scan
            return TargetDecision(
                has_target=False,
                target_visible=False,
                should_pursue=False,
                should_scan=True,
                should_reposition=False,
                center_error_x=0.0,
                center_error_y=0.0,
                reason=f"target_lost_{lost_sec:.1f}s",
                confidence_ema=self._track.confidence_ema,
                lost_ms=lost_sec * 1000,
            )

        cx, cy = screen_center
        err_x, err_y = 0.0, 0.0
        if self._track.bbox is not None:
            x, y, w, h = self._track.bbox
            err_x = (x + w / 2) - cx
            err_y = (y + h / 2) - cy

        in_deadzone = abs(err_x) < self._deadzone_px and abs(err_y) < self._deadzone_px

        return TargetDecision(
            has_target=True,
            target_visible=self._track.bbox is not None,
            should_pursue=not in_deadzone,
            should_scan=False,
            should_reposition=False,
            center_error_x=err_x,
            center_error_y=err_y,
            reason="tracking" if self._track.bbox else f"memory_{lost_sec:.1f}s",
            confidence_ema=self._track.confidence_ema,
            lost_ms=lost_sec * 1000,
        )

    def _default_decision(self, reason: str) -> TargetDecision:
        return TargetDecision(
            has_target=False,
            target_visible=False,
            should_pursue=False,
            should_scan=True,
            should_reposition=False,
            center_error_x=0.0,
            center_error_y=0.0,
            reason=reason,
            confidence_ema=0.0,
            lost_ms=0.0,
        )

    def get_track(self) -> Optional[TargetTrack]:
        """Return current target track for telemetry."""
        return self._track
