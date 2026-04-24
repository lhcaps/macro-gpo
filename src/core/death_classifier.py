"""
Death Classifier — Phase 12.5.

Classifies the death reason from the last N telemetry ticks.
Produces a DeathReason label + metadata dict attached to Discord death events.

Design decisions:
- Runs at death time, reads last telemetry ticks from MatchTelemetry
- Rule-based classifier: checks conditions in priority order
- Returns unknown if telemetry is empty (graceful degradation)
- Classifier is pure and stateless — no side effects
- Phase 12.4 Discord death event path is preserved exactly
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

DeathReason = Literal[
    "combat_death",
    "crowd_death",
    "zone_death",
    "stuck_death",
    "target_lost_death",
    "unknown",
]

# ---------------------------------------------------------------------------
# DeathClassification dataclass
# ---------------------------------------------------------------------------

@dataclass
class DeathClassification:
    """The result of classifying a death event."""
    reason: DeathReason = "unknown"
    confidence: float = 0.0           # 0.0-1.0 confidence in this classification
    last_state: str = "unknown"
    crowd_risk: float = 0.0
    visible_enemy_count: int = 0
    target_lost_ms: float = 0.0
    player_hp_low: bool = False
    edge_risk: float = 0.0
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ---------------------------------------------------------------------------
# DeathClassifier
# ---------------------------------------------------------------------------

class DeathClassifier:
    """
    Classifies death reason from last N telemetry ticks.

    Usage:
        classifier = DeathClassifier(config)
        result = classifier.classify(last_ticks)  # From MatchTelemetry.get_last_ticks()
    """

    # Risk thresholds
    CROWD_RISK_DEATH_THRESHOLD = 0.70
    EDGE_RISK_DEATH_THRESHOLD = 0.70
    STUCK_SCORE_DEATH_THRESHOLD = 0.70
    TARGET_LOST_DEATH_THRESHOLD_MS = 3000

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("combat_ai", {})
        self._enabled = cfg.get("death_classifier_enabled", True)

    def classify(self, last_ticks: list[dict]) -> DeathClassification:
        """
        Classify death reason from last telemetry ticks.

        Args:
            last_ticks: List of dicts from MatchTelemetry.get_last_ticks()
                        Each tick has: state, signals, risk, target, decision

        Returns:
            DeathClassification with reason, confidence, and metadata
        """
        if not self._enabled or not last_ticks:
            return DeathClassification(reason="unknown", confidence=0.0)

        # Extract the last non-transition, non-event tick as the death context
        death_ctx = None
        for tick in reversed(last_ticks):
            state = tick.get("state", "")
            if state not in ("EVENT", "transition") and "→" not in str(state):
                death_ctx = tick
                break

        if death_ctx is None:
            death_ctx = last_ticks[-1]

        # Extract fields
        last_state = death_ctx.get("state", "unknown")
        signals = death_ctx.get("signals", {})
        risk = death_ctx.get("risk", {})
        target = death_ctx.get("target", {})
        decision = death_ctx.get("decision", {})

        # Gather metrics
        crowd_risk = risk.get("crowd_risk", 0.0) if isinstance(risk, dict) else 0.0
        death_risk = risk.get("death_risk", 0.0) if isinstance(risk, dict) else 0.0
        visible_enemy_count = risk.get("visible_enemy_count", 0) if isinstance(risk, dict) else 0
        target_lost_ms = target.get("lost_ms", 0.0) if isinstance(target, dict) else 0.0
        player_hp_low = signals.get("player_hp_low", False) if isinstance(signals, dict) else False
        in_combat = signals.get("in_combat", False) if isinstance(signals, dict) else False
        hit_confirmed = signals.get("hit_confirmed", False) if isinstance(signals, dict) else False
        edge_risk = risk.get("edge_risk", 0.0) if isinstance(risk, dict) else 0.0

        # Classify using rule-based approach (in priority order)
        reason, confidence, breakdown = self._classify(
            crowd_risk=crowd_risk,
            visible_enemy_count=visible_enemy_count,
            in_combat=in_combat,
            hit_confirmed=hit_confirmed,
            player_hp_low=player_hp_low,
            target_lost_ms=target_lost_ms,
            edge_risk=edge_risk,
            death_risk=death_risk,
        )

        return DeathClassification(
            reason=reason,
            confidence=confidence,
            last_state=last_state,
            crowd_risk=crowd_risk,
            visible_enemy_count=visible_enemy_count,
            target_lost_ms=target_lost_ms,
            player_hp_low=player_hp_low,
            edge_risk=edge_risk,
            metadata=breakdown,
        )

    def _classify(
        self,
        crowd_risk: float,
        visible_enemy_count: int,
        in_combat: bool,
        hit_confirmed: bool,
        player_hp_low: bool,
        target_lost_ms: float,
        edge_risk: float,
        death_risk: float,
    ) -> tuple[DeathReason, float, dict]:
        """
        Apply classification rules in priority order.

        Rules:
        1. crowd_death: in_combat AND crowd_risk >= 0.70 AND >= 2 visible enemies
        2. combat_death: in_combat OR hit_confirmed (but not crowd_death)
        3. zone_death: edge_risk >= 0.70 (zone hazard damage)
        4. stuck_death: stuck_score >= 0.70 (not yet implemented — placeholder)
        5. target_lost_death: target_lost_ms >= 3000 (lost target, died trying to find it)
        6. unknown: fallback
        """
        breakdown = {
            "crowd_risk": crowd_risk,
            "visible_enemy_count": visible_enemy_count,
            "in_combat": in_combat,
            "hit_confirmed": hit_confirmed,
            "player_hp_low": player_hp_low,
            "target_lost_ms": target_lost_ms,
            "edge_risk": edge_risk,
            "death_risk": death_risk,
        }

        # Rule 1: Crowd death — multi-enemy fight, high risk
        if in_combat and crowd_risk >= self.CROWD_RISK_DEATH_THRESHOLD and visible_enemy_count >= 2:
            breakdown["rule_matched"] = "crowd_death"
            confidence = min(1.0, 0.5 + crowd_risk * 0.5)
            return "crowd_death", confidence, breakdown

        # Rule 2: Combat death — died in a fight (not necessarily crowd)
        if in_combat or hit_confirmed:
            breakdown["rule_matched"] = "combat_death"
            confidence = 0.7 if in_combat else 0.5
            return "combat_death", confidence, breakdown

        # Rule 3: Zone death — edge/zone hazard damage
        if edge_risk >= self.EDGE_RISK_DEATH_THRESHOLD:
            breakdown["rule_matched"] = "zone_death"
            confidence = 0.6
            return "zone_death", confidence, breakdown

        # Rule 4: Stuck death — bot stuck and couldn't act (placeholder for now)
        # This would need a "stuck_score" in risk dict, which plan 03 doesn't produce yet
        # Placeholder: return unknown until stuck detection is added
        # if stuck_score >= self.STUCK_SCORE_DEATH_THRESHOLD:
        #     breakdown["rule_matched"] = "stuck_death"
        #     return "stuck_death", 0.6, breakdown

        # Rule 5: Target lost death — target gone for too long
        if target_lost_ms >= self.TARGET_LOST_DEATH_THRESHOLD_MS:
            breakdown["rule_matched"] = "target_lost_death"
            confidence = 0.6
            return "target_lost_death", confidence, breakdown

        # Rule 6: Unknown
        breakdown["rule_matched"] = "unknown"
        return "unknown", 0.3, breakdown

    def classify_from_telemetry(self, telemetry_instance) -> DeathClassification:
        """
        Convenience method: read last ticks from telemetry instance and classify.

        Args:
            telemetry_instance: MatchTelemetry instance

        Returns:
            DeathClassification
        """
        last_ticks = telemetry_instance.get_last_ticks(20)
        return self.classify(last_ticks)
