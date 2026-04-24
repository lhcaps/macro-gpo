"""
Movement Policy — Phase 12.5.

Scores and selects combat movement actions based on situation context.
Replaces pure-random pattern selection in `perform_dynamic_combat_movement()`.

Design decisions:
- Scoring is additive: each factor adds or subtracts from base score
- Repeated action penalty prevents stuttering on the same action
- Random fallback ensures bot always moves even with incomplete context
- Intent from situation model maps to movement category
- Existing `perform_dynamic_combat_movement()` is preserved as backward-compatible wrapper
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

MovementAction = Literal[
    "strafe_left",
    "strafe_right",
    "forward_left",
    "forward_right",
    "backward_left",
    "backward_right",
    "short_backstep",
    "camera_correct_left",
    "camera_correct_right",
    "scan_left",
    "scan_right",
    "hold_position",
]

# ---------------------------------------------------------------------------
# Action Definition
# ---------------------------------------------------------------------------

@dataclass
class ScoredAction:
    """An action candidate with its computed score."""
    name: MovementAction
    score: float
    reason: str
    keys: list[str]
    duration_range: tuple[float, float]


# ---------------------------------------------------------------------------
# MovementPolicy
# ---------------------------------------------------------------------------

class MovementPolicy:
    """
    Scores and selects movement actions based on combat situation.

    Usage:
        policy = MovementPolicy(config)
        action = policy.choose_action(
            intent="reposition",
            situation=situation,
            target_decision=target_dec,
            last_action="strafe_left",
        )
        # action.name, action.keys, action.duration_range
    """

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("combat_ai", {})
        self._enabled = cfg.get("movement_policy") == "scored"
        self._fallback_random = cfg.get("random_movement_fallback", True)
        self._repeat_penalty = cfg.get("repeated_action_penalty", 0.15)
        self._reposition_threshold = cfg.get("reposition_crowd_threshold", 0.70)
        self._flee_hp_threshold = cfg.get("flee_crowd_hp_threshold", 0.55)

        self._last_action: Optional[MovementAction] = None
        self._last_action_ts: float = 0.0

    def reset(self) -> None:
        """Reset policy state for new match."""
        self._last_action = None
        self._last_action_ts = 0.0

    def choose_action(
        self,
        intent: str,
        situation,
        target_decision=None,
        last_action: Optional[str] = None,
    ) -> ScoredAction:
        """
        Choose the best movement action for the current situation.

        Args:
            intent: recommended intent from situation model
            situation: CombatSituation with crowd_risk, player_hp_low, etc.
            target_decision: TargetDecision with center_error_x/y
            last_action: name of the previously selected action

        Returns:
            ScoredAction with name, score, reason, keys, duration_range
        """
        if not self._enabled:
            return self._random_fallback()

        crowd_risk = getattr(situation, "crowd_risk", 0.0) if situation else 0.0
        player_hp_low = getattr(situation, "player_hp_low", False) if situation else False
        death_risk = getattr(situation, "death_risk", 0.0) if situation else 0.0
        target_visible = getattr(target_decision, "target_visible", False) if target_decision else False

        err_x = getattr(target_decision, "center_error_x", 0.0) if target_decision else 0.0
        err_y = getattr(target_decision, "center_error_y", 0.0) if target_decision else 0.0

        candidates = self._get_candidates_for_intent(intent, err_x, err_y)

        scored = []
        for candidate in candidates:
            score = self._score_action(
                action=candidate,
                intent=intent,
                crowd_risk=crowd_risk,
                player_hp_low=player_hp_low,
                target_visible=target_visible,
                err_x=err_x,
                err_y=err_y,
                last_action=last_action or self._last_action,
            )
            scored.append((score, candidate))

        scored.sort(key=lambda x: x[0].score, reverse=True)
        best = scored[0][0]

        self._last_action = best.name
        self._last_action_ts = time.time()

        if best.score < -0.3 and self._fallback_random:
            return self._random_fallback()

        return best

    def _get_candidates_for_intent(
        self,
        intent: str,
        err_x: float,
        err_y: float,
    ) -> list[ScoredAction]:
        """Get available movement actions for a given intent."""
        base = [
            ScoredAction("strafe_left", 0.0, "base", ["a"], (0.11, 0.20)),
            ScoredAction("strafe_right", 0.0, "base", ["d"], (0.11, 0.20)),
            ScoredAction("short_backstep", 0.0, "base", ["s"], (0.10, 0.18)),
            ScoredAction("hold_position", 0.0, "base", [], (0.05, 0.12)),
        ]

        if intent == "engage":
            return base + [
                ScoredAction("forward_left", 0.0, "engage", ["w", "a"], (0.14, 0.24)),
                ScoredAction("forward_right", 0.0, "engage", ["w", "d"], (0.14, 0.24)),
                ScoredAction("camera_correct_left", 0.0, "engage", [], (0.08, 0.15)),
                ScoredAction("camera_correct_right", 0.0, "engage", [], (0.08, 0.15)),
            ]

        elif intent == "pursue":
            toward = []
            if err_x < -30:
                toward.append(ScoredAction("camera_correct_right", 0.0, "pursue", [], (0.08, 0.15)))
            elif err_x > 30:
                toward.append(ScoredAction("camera_correct_left", 0.0, "pursue", [], (0.08, 0.15)))
            return base + toward + [
                ScoredAction("forward_left", 0.0, "pursue", ["w", "a"], (0.14, 0.24)),
                ScoredAction("forward_right", 0.0, "pursue", ["w", "d"], (0.14, 0.24)),
            ]

        elif intent == "reposition":
            return [
                ScoredAction("backward_left", 0.0, "reposition", ["s", "a"], (0.12, 0.20)),
                ScoredAction("backward_right", 0.0, "reposition", ["s", "d"], (0.12, 0.20)),
                ScoredAction("short_backstep", 0.0, "reposition", ["s"], (0.15, 0.25)),
                ScoredAction("strafe_left", 0.0, "reposition", ["a"], (0.11, 0.20)),
                ScoredAction("strafe_right", 0.0, "reposition", ["d"], (0.11, 0.20)),
                ScoredAction("hold_position", 0.0, "reposition", [], (0.05, 0.12)),
            ]

        elif intent == "flee":
            return [
                ScoredAction("backward_left", 0.0, "flee", ["s", "a"], (0.20, 0.35)),
                ScoredAction("backward_right", 0.0, "flee", ["s", "d"], (0.20, 0.35)),
                ScoredAction("short_backstep", 0.0, "flee", ["s"], (0.20, 0.35)),
                ScoredAction("strafe_left", 0.0, "flee", ["a"], (0.15, 0.25)),
                ScoredAction("strafe_right", 0.0, "flee", ["d"], (0.15, 0.25)),
            ]

        elif intent == "scan":
            return [
                ScoredAction("scan_left", 0.0, "scan", [], (0.15, 0.25)),
                ScoredAction("scan_right", 0.0, "scan", [], (0.15, 0.25)),
                ScoredAction("strafe_left", 0.0, "scan", ["a"], (0.10, 0.18)),
                ScoredAction("strafe_right", 0.0, "scan", ["d"], (0.10, 0.18)),
                ScoredAction("hold_position", 0.0, "scan", [], (0.05, 0.12)),
            ]

        return base

    def _score_action(
        self,
        action: ScoredAction,
        intent: str,
        crowd_risk: float,
        player_hp_low: bool,
        target_visible: bool,
        err_x: float,
        err_y: float,
        last_action: Optional[str],
    ) -> ScoredAction:
        """
        Score a single action candidate.

        Score = sum of factors:
        - target_visible_score: +0.3 if target visible
        - target_centering_score: +0.2 if camera correction helps center target
        - hit_confirm_score: +0.1 if recent hit confirm
        - spacing_score: +0.2 if reposition/flee and crowd risk high
        - escape_vector_score: +0.2 if backward in flee/reposition
        - crowd_risk_penalty: -0.3 if forward engage in high crowd risk
        - repeated_action_penalty: -0.15 if same as last action
        - target_switch_penalty: -0.2 if moving away from target when visible
        """
        score = 0.0
        reasons = []

        if target_visible:
            score += 0.30
            reasons.append("target_visible")

        if "camera_correct" in action.name:
            if abs(err_x) > 50 or abs(err_y) > 50:
                score += 0.20
                reasons.append("centering_needed")
            else:
                score -= 0.10
                reasons.append("already_centered")

        if action.name in ("forward_left", "forward_right"):
            if intent in ("engage", "pursue"):
                score += 0.20
                reasons.append("forward_engage")
            elif crowd_risk > 0.5:
                score -= 0.30
                reasons.append("forward_crowd_penalty")
            else:
                score -= 0.10

        if action.name in ("backward_left", "backward_right", "short_backstep"):
            if intent in ("reposition", "flee"):
                score += 0.25
                reasons.append("backward_escape")
            elif crowd_risk > 0.4:
                score += 0.10
                reasons.append("backward_crowd_caution")
            else:
                score -= 0.05

        if action.name in ("strafe_left", "strafe_right"):
            if intent == "reposition":
                score += 0.15
                reasons.append("strafe_reposition")
            elif intent == "engage":
                score += 0.10
                reasons.append("strafe_engage")
            else:
                score += 0.05

        if action.name in ("scan_left", "scan_right"):
            if intent == "scan":
                score += 0.30
                reasons.append("scan_intent")
            elif intent == "pursue":
                score += 0.10
                reasons.append("scan_pursue")
            else:
                score -= 0.20

        if action.name == "hold_position":
            if intent in ("reposition", "flee"):
                score += 0.05
            else:
                score -= 0.05

        if crowd_risk >= self._reposition_threshold:
            if action.name in ("forward_left", "forward_right"):
                score -= 0.30
                reasons.append("crowd_forward_penalty")
            elif action.name in ("backward_left", "backward_right", "short_backstep"):
                score += 0.15
                reasons.append("crowd_backward_bonus")

        if player_hp_low:
            if action.name in ("forward_left", "forward_right"):
                score -= 0.25
                reasons.append("lowhp_forward_penalty")
            elif action.name in ("backward_left", "backward_right", "short_backstep"):
                score += 0.20
                reasons.append("lowhp_backward_bonus")
            elif action.name in ("strafe_left", "strafe_right"):
                score += 0.10

        if action.name == last_action:
            score -= self._repeat_penalty
            reasons.append("repeat_penalty")

        return ScoredAction(
            name=action.name,
            score=score,
            reason="|".join(reasons) if reasons else "neutral",
            keys=action.keys,
            duration_range=action.duration_range,
        )

    def _random_fallback(self) -> ScoredAction:
        """Pure random fallback when policy is disabled or score is negative."""
        patterns = [
            ScoredAction("strafe_left", 0.0, "random", ["a"], (0.11, 0.20)),
            ScoredAction("strafe_right", 0.0, "random", ["d"], (0.11, 0.20)),
            ScoredAction("forward_left", 0.0, "random", ["w", "a"], (0.14, 0.24)),
            ScoredAction("forward_right", 0.0, "random", ["w", "d"], (0.14, 0.24)),
            ScoredAction("backward_left", 0.0, "random", ["s", "a"], (0.10, 0.18)),
            ScoredAction("backward_right", 0.0, "random", ["s", "d"], (0.10, 0.18)),
            ScoredAction("short_backstep", 0.0, "random", ["s"], (0.16, 0.28)),
        ]
        return random.choice(patterns)
