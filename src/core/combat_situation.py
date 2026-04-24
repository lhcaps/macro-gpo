"""
Combat Situation Model — Phase 12.5.

Computes a situation assessment from combat signals and target memory output,
producing crowd_risk and recommended_intent scores used by movement policy.

Design decisions:
- No new FSM states — intent is a recommendation, not a state machine change
- Intent is advisory: movement policy receives it but FLEEING still overrides
- Risk formula is tunable via config (no hardcoded magic numbers in logic)
- Crowd risk and death risk are computed independently, merged at the end
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Intent = Literal["engage", "pursue", "reposition", "flee", "scan"]
DistanceBand = Literal["close", "mid", "far", "unknown"]

# ---------------------------------------------------------------------------
# CombatSituation dataclass
# ---------------------------------------------------------------------------

@dataclass
class CombatSituation:
    """A snapshot of the current combat situation."""
    visible_enemy_count: int = 0
    nearby_enemy_count: int = 0
    target_centered: bool = False
    target_distance_band: DistanceBand = "unknown"
    hit_confirm_recent: bool = False
    in_combat: bool = False
    player_hp_low: bool = False
    crowd_risk: float = 0.0
    target_loss_risk: float = 0.0
    death_risk: float = 0.0
    recommended_intent: Intent = "scan"
    crowd_risk_breakdown: dict = None

    def __post_init__(self):
        if self.crowd_risk_breakdown is None:
            self.crowd_risk_breakdown = {}


# ---------------------------------------------------------------------------
# CombatSituationModel
# ---------------------------------------------------------------------------

class CombatSituationModel:
    """
    Computes crowd_risk and recommended_intent from combat signals + target memory.

    Usage:
        model = CombatSituationModel(config)
        situation = model.assess(
            signals=signals,
            target_decision=target_dec,
            visible_enemy_count=3,
        )
        # situation.crowd_risk, situation.recommended_intent
    """

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("combat_ai", {})
        self._enabled = cfg.get("situation_model_enabled", True)
        self._crowd_threshold = cfg.get("crowd_risk_threshold", 0.70)
        self._nearby_crowd_count = cfg.get("nearby_enemy_crowd_count", 2)
        self._visible_crowd_count = cfg.get("visible_enemy_crowd_count", 3)
        self._hit_confirm_window = 3.0  # seconds

        self._last_hit_confirm_ts: float = 0.0

    def assess(
        self,
        signals: dict,
        target_decision,
        visible_enemy_count: int = 0,
        target_confidence_ema: float = 0.0,
    ) -> CombatSituation:
        """
        Compute combat situation from signals and target memory.

        Args:
            signals: CombatSignalDetector.scan_all_signals() output
            target_decision: TargetDecision from TargetMemory.update()
            visible_enemy_count: Number of visible enemies (from YOLO)
            target_confidence_ema: EMA confidence of current target

        Returns:
            CombatSituation with crowd_risk and recommended_intent
        """
        if not self._enabled:
            return CombatSituation(recommended_intent="scan")

        now = time.time()
        hit_confirmed = signals.get("hit_confirmed", False)
        in_combat = signals.get("in_combat", False)
        player_hp_low = signals.get("player_hp_low", False)
        enemy_nearby = signals.get("enemy_nearby", False)

        if hit_confirmed:
            self._last_hit_confirm_ts = now

        hit_confirm_recent = (now - self._last_hit_confirm_ts) < self._hit_confirm_window

        # --- Target centered check ---
        if target_decision is not None:
            center_err_x = getattr(target_decision, "center_error_x", 0.0)
            center_err_y = getattr(target_decision, "center_error_y", 0.0)
            target_centered = (
                abs(center_err_x) < 90 and abs(center_err_y) < 90
            )
            has_target = getattr(target_decision, "has_target", False)
            target_visible = getattr(target_decision, "target_visible", False)
        else:
            center_err_x = center_err_y = 0.0
            target_centered = False
            has_target = target_visible = False

        # --- Nearby enemy estimate ---
        if visible_enemy_count > 0:
            nearby_enemy_count = visible_enemy_count
        elif in_combat or enemy_nearby:
            nearby_enemy_count = 1
        else:
            nearby_enemy_count = 0

        # --- Crowd risk formula ---
        crowd_risk, breakdown = self._compute_crowd_risk(
            visible_enemy_count=visible_enemy_count,
            nearby_enemy_count=nearby_enemy_count,
            target_centered=target_centered,
            hit_confirm_recent=hit_confirm_recent,
            player_hp_low=player_hp_low,
            has_target=has_target,
        )

        # --- Target loss risk ---
        target_loss_risk = 0.0
        if target_decision is not None:
            lost_ms = getattr(target_decision, "lost_ms", 0.0)
            if lost_ms > 2000:
                target_loss_risk = min(1.0, (lost_ms - 2000) / 3000.0)
            if target_confidence_ema < 0.3:
                target_loss_risk += 0.3

        # --- Death risk ---
        death_risk = self._compute_death_risk(
            crowd_risk=crowd_risk,
            player_hp_low=player_hp_low,
            target_loss_risk=target_loss_risk,
        )

        # --- Recommended intent ---
        intent = self._decide_intent(
            crowd_risk=crowd_risk,
            death_risk=death_risk,
            player_hp_low=player_hp_low,
            has_target=has_target,
            target_visible=target_visible,
            target_centered=target_centered,
            nearby_enemy_count=nearby_enemy_count,
            hit_confirm_recent=hit_confirm_recent,
        )

        return CombatSituation(
            visible_enemy_count=visible_enemy_count,
            nearby_enemy_count=nearby_enemy_count,
            target_centered=target_centered,
            target_distance_band="unknown",
            hit_confirm_recent=hit_confirm_recent,
            in_combat=in_combat,
            player_hp_low=player_hp_low,
            crowd_risk=crowd_risk,
            target_loss_risk=target_loss_risk,
            death_risk=death_risk,
            recommended_intent=intent,
            crowd_risk_breakdown=breakdown,
        )

    def _compute_crowd_risk(
        self,
        visible_enemy_count: int,
        nearby_enemy_count: int,
        target_centered: bool,
        hit_confirm_recent: bool,
        player_hp_low: bool,
        has_target: bool,
    ) -> tuple[float, dict]:
        """
        Compute crowd risk as a weighted sum.

        crowd_risk = sum of risk factors, clamped to [0, 1]

        Factors:
        - +0.30 if visible_enemy_count >= 2
        - +0.35 if nearby_enemy_count >= 2
        - +0.20 if target not centered
        - +0.20 if no hit_confirm_recent
        - +0.35 if player_hp_low
        """
        breakdown = {}
        risk = 0.0

        if visible_enemy_count >= 2:
            risk += 0.30
            breakdown["visible_enemy_2+"] = 0.30
        else:
            breakdown["visible_enemy_2+"] = 0.0

        if nearby_enemy_count >= 2:
            risk += 0.35
            breakdown["nearby_enemy_2+"] = 0.35
        else:
            breakdown["nearby_enemy_2+"] = 0.0

        if not target_centered:
            risk += 0.20
            breakdown["target_not_centered"] = 0.20
        else:
            breakdown["target_not_centered"] = 0.0

        if not hit_confirm_recent:
            risk += 0.20
            breakdown["no_hit_confirm"] = 0.20
        else:
            breakdown["no_hit_confirm"] = 0.0

        if player_hp_low:
            risk += 0.35
            breakdown["player_hp_low"] = 0.35
        else:
            breakdown["player_hp_low"] = 0.0

        risk = max(0.0, min(1.0, risk))
        breakdown["total"] = risk

        return risk, breakdown

    def _compute_death_risk(
        self,
        crowd_risk: float,
        player_hp_low: bool,
        target_loss_risk: float,
    ) -> float:
        """Compute overall death risk as a combination of factors."""
        death_risk = crowd_risk * 0.5
        if player_hp_low:
            death_risk += 0.40
        death_risk += target_loss_risk * 0.2
        return max(0.0, min(1.0, death_risk))

    def _decide_intent(
        self,
        crowd_risk: float,
        death_risk: float,
        player_hp_low: bool,
        has_target: bool,
        target_visible: bool,
        target_centered: bool,
        nearby_enemy_count: int,
        hit_confirm_recent: bool,
    ) -> Intent:
        """
        Decide recommended intent based on situation.

        Rules (in priority order):
        1. player_hp_low + nearby enemies -> flee
        2. crowd_risk >= threshold -> reposition
        3. target_visible + target_centered -> engage
        4. has_target (even if not centered) -> pursue
        5. otherwise -> scan
        """
        if player_hp_low and nearby_enemy_count >= 1:
            return "flee"

        if crowd_risk >= self._crowd_threshold:
            return "reposition"

        if target_visible and target_centered:
            return "engage"

        if has_target:
            return "pursue"

        return "scan"
