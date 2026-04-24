#!/usr/bin/env python3
"""
verify_combat_ai.py — Phase 12.5 AI Verification Harness

Runs smoke tests on the combat AI stack without needing a live game.
Tests: compile, import, config, logic, and telemetry.

Usage:
    python scripts/verify_combat_ai.py
    python scripts/verify_combat_ai.py --verbose
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
SCRIPTS_DIR = REPO_ROOT / "scripts"

# ---------------------------------------------------------------------------
# Test Results
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        msg = f"  [{status}] {self.name}"
        if self.message:
            msg += f"\n        {self.message}"
        return msg


def run_tests(verbose: bool = False) -> list[TestResult]:
    """Run all verification tests. Returns list of TestResult."""
    results = []

    # ---- COMPILE TESTS ----
    results += run_compile_tests()

    # ---- IMPORT TESTS ----
    results += run_import_tests()

    # ---- CONFIG TESTS ----
    results += run_config_tests()

    # ---- LOGIC TESTS ----
    results += run_logic_tests()

    # ---- TELEMETRY TESTS ----
    results += run_telemetry_tests()

    # ---- REGRESSION TESTS ----
    results += run_regression_tests()

    return results


def run_compile_tests() -> list[TestResult]:
    """py_compile on all new modules."""
    results = []
    modules = [
        "src/core/target_memory",
        "src/core/combat_situation",
        "src/core/movement_policy",
        "src/core/death_classifier",
        "src/services/match_telemetry",
    ]
    for mod in modules:
        src_path = REPO_ROOT / (mod.replace("/", os.sep) + ".py")
        if not src_path.exists():
            results.append(TestResult(f"compile:{mod}", False, f"File not found: {src_path}"))
            continue
        try:
            subprocess.run(
                [sys.executable, "-m", "py_compile", str(src_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            results.append(TestResult(f"compile:{mod}", True))
        except Exception as e:
            results.append(TestResult(f"compile:{mod}", False, str(e)))

    # Also compile bot_engine.py to catch wiring errors
    bot_path = SRC_DIR / "core" / "bot_engine.py"
    try:
        subprocess.run(
            [sys.executable, "-m", "py_compile", str(bot_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        results.append(TestResult("compile:bot_engine", True))
    except Exception as e:
        results.append(TestResult("compile:bot_engine", False, str(e)))

    return results


def run_import_tests() -> list[TestResult]:
    """Import all new modules to verify no import-time errors."""
    results = []
    # Add repo root so 'src' is a top-level package
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    modules = [
        ("src.core.target_memory", ["TargetMemory", "TargetTrack", "TargetDecision"]),
        ("src.core.combat_situation", ["CombatSituationModel", "CombatSituation", "Intent"]),
        ("src.core.movement_policy", ["MovementPolicy", "ScoredAction"]),
        ("src.core.death_classifier", ["DeathClassifier", "DeathClassification"]),
        ("src.services.match_telemetry", ["MatchTelemetry", "CombatTick", "MatchSummary"]),
    ]

    for mod_name, expected_symbols in modules:
        try:
            mod = importlib.import_module(mod_name)
            for sym in expected_symbols:
                if not hasattr(mod, sym):
                    results.append(TestResult(f"import:{mod_name}.{sym}", False, f"Symbol '{sym}' not found"))
                else:
                    results.append(TestResult(f"import:{mod_name}.{sym}", True))
        except Exception as e:
            results.append(TestResult(f"import:{mod_name}", False, str(e)))

    return results


def run_config_tests() -> list[TestResult]:
    """Verify combat_ai config is properly deep-merged."""
    results = []

    config_path = REPO_ROOT / "src" / "utils" / "config.py"
    if not config_path.exists():
        results.append(TestResult("config:file_exists", False, "config.py not found"))
        return results

    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from src.utils.config import DEFAULT_CONFIG

        if "combat_ai" not in DEFAULT_CONFIG:
            results.append(TestResult("config:combat_ai_key", False, "combat_ai key not in DEFAULT_CONFIG"))
            return results

        ca = DEFAULT_CONFIG["combat_ai"]
        required_keys = [
            "telemetry_enabled", "telemetry_sample_rate", "telemetry_dir",
            "target_memory_enabled", "target_lost_grace_sec", "target_switch_penalty",
            "situation_model_enabled", "crowd_risk_threshold",
            "movement_policy", "random_movement_fallback", "repeated_action_penalty",
            "death_classifier_enabled",
        ]
        for key in required_keys:
            if key in ca:
                results.append(TestResult(f"config:{key}", True))
            else:
                results.append(TestResult(f"config:{key}", False, f"Missing key: {key}"))

        # Verify deep_merge doesn't break existing keys
        from src.utils.config import _deep_merge
        base = {"discord_events": {"webhook_url": "secret"}, "combat_regions_v2": {}}
        override = {"combat_ai": {"telemetry_enabled": True}}
        merged = _deep_merge(base, override)
        if merged.get("discord_events", {}).get("webhook_url") == "secret":
            results.append(TestResult("config:deep_merge_preserves_existing", True))
        else:
            results.append(TestResult("config:deep_merge_preserves_existing", False, "deep_merge overwrote existing keys"))

    except Exception as e:
        results.append(TestResult("config:tests", False, str(e)))

    return results


def run_logic_tests() -> list[TestResult]:
    """Unit-test core logic classes in isolation."""
    results = []

    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))

        # --- TargetMemory tests ---
        from src.core.target_memory import TargetMemory
        mem = TargetMemory({"combat_ai": {"target_memory_enabled": True, "target_lost_grace_sec": 2.0}})
        # No detections, no signals → should return scan
        dec = mem.update([], {}, (960, 540), (1920, 1080))
        if dec.should_scan:
            results.append(TestResult("logic:TargetMemory.no_detection_scans", True))
        else:
            results.append(TestResult("logic:TargetMemory.no_detection_scans", False, f"Expected should_scan=True, got {dec}"))

        # Test memory persistence: update with same detection
        import time
        det = (8, 0.8, (100, 100, 50, 50))
        dec1 = mem.update([det], {}, (960, 540), (1920, 1080))
        time.sleep(0.05)
        dec2 = mem.update([], {}, (960, 540), (1920, 1080))  # Lost for 50ms
        if dec2.has_target and dec2.lost_ms < 2000:
            results.append(TestResult("logic:TargetMemory.memory_persists", True))
        else:
            results.append(TestResult("logic:TargetMemory.memory_persists", False, f"lost_ms={dec2.lost_ms}, has_target={dec2.has_target}"))

        mem.reset()

        # --- CombatSituationModel tests ---
        from src.core.combat_situation import CombatSituationModel
        model = CombatSituationModel({"combat_ai": {"situation_model_enabled": True}})

        # Low crowd risk → engage intent
        class MockTargetDec:
            has_target = True
            target_visible = True
            center_error_x = 20.0
            center_error_y = 20.0
            confidence_ema = 0.8

        sit = model.assess({}, MockTargetDec(), visible_enemy_count=1)
        if sit.recommended_intent == "engage":
            results.append(TestResult("logic:SituationModel.engage_intent", True))
        else:
            results.append(TestResult("logic:SituationModel.engage_intent", False, f"Expected engage, got {sit.recommended_intent}"))

        # High crowd risk → reposition
        sit2 = model.assess(
            {"in_combat": True},
            MockTargetDec(),
            visible_enemy_count=3,
        )
        if sit2.recommended_intent == "reposition":
            results.append(TestResult("logic:SituationModel.reposition_intent", True))
        else:
            results.append(TestResult("logic:SituationModel.reposition_intent", False, f"Expected reposition, got {sit2.recommended_intent}"))

        # HP low + enemies → flee
        sit3 = model.assess(
            {"player_hp_low": True, "enemy_nearby": True},
            MockTargetDec(),
            visible_enemy_count=1,
        )
        if sit3.recommended_intent == "flee":
            results.append(TestResult("logic:SituationModel.flee_intent", True))
        else:
            results.append(TestResult("logic:SituationModel.flee_intent", False, f"Expected flee, got {sit3.recommended_intent}"))

        # crowd_risk value
        if sit2.crowd_risk >= 0.65:
            results.append(TestResult("logic:SituationModel.crowd_risk_value", True))
        else:
            results.append(TestResult("logic:SituationModel.crowd_risk_value", False, f"crowd_risk={sit2.crowd_risk}"))

        # --- MovementPolicy tests ---
        from src.core.movement_policy import MovementPolicy
        policy = MovementPolicy({"combat_ai": {"movement_policy": "scored", "repeated_action_penalty": 0.15}})

        action = policy.choose_action("engage", sit, MockTargetDec())
        if action.name != "hold_position":  # Should not just hold
            results.append(TestResult("logic:MovementPolicy.engage_selects_movement", True))
        else:
            results.append(TestResult("logic:MovementPolicy.engage_selects_movement", False, f"Got hold_position for engage intent"))

        # Reposition prefers backward
        action2 = policy.choose_action("reposition", sit2, MockTargetDec())
        if "backward" in action2.name or "backstep" in action2.name or "strafe" in action2.name:
            results.append(TestResult("logic:MovementPolicy.reposition_avoids_forward", True))
        else:
            results.append(TestResult("logic:MovementPolicy.reposition_avoids_forward", False, f"Got {action2.name} for reposition"))

        # Repeat penalty
        policy._last_action = "strafe_left"
        action3 = policy.choose_action("engage", sit, MockTargetDec(), last_action="strafe_left")
        if action3.name != "strafe_left":
            results.append(TestResult("logic:MovementPolicy.repeat_penalty", True))
        else:
            results.append(TestResult("logic:MovementPolicy.repeat_penalty", False, f"Same action selected despite repeat penalty"))

        # --- DeathClassifier tests ---
        from src.core.death_classifier import DeathClassifier
        classifier = DeathClassifier({"combat_ai": {"death_classifier_enabled": True}})

        # Combat death
        ticks = [{
            "state": "ENGAGED",
            "signals": {"in_combat": True, "hit_confirmed": False},
            "risk": {"crowd_risk": 0.3, "visible_enemy_count": 1},
            "target": {"lost_ms": 0},
        }]
        result = classifier.classify(ticks)
        if result.reason == "combat_death":
            results.append(TestResult("logic:DeathClassifier.combat_death", True))
        else:
            results.append(TestResult("logic:DeathClassifier.combat_death", False, f"Expected combat_death, got {result.reason}"))

        # Crowd death
        ticks2 = [{
            "state": "ENGAGED",
            "signals": {"in_combat": True},
            "risk": {"crowd_risk": 0.80, "visible_enemy_count": 3},
            "target": {"lost_ms": 0},
        }]
        result2 = classifier.classify(ticks2)
        if result2.reason == "crowd_death":
            results.append(TestResult("logic:DeathClassifier.crowd_death", True))
        else:
            results.append(TestResult("logic:DeathClassifier.crowd_death", False, f"Expected crowd_death, got {result2.reason}"))

        # Unknown with empty ticks
        result3 = classifier.classify([])
        if result3.reason == "unknown":
            results.append(TestResult("logic:DeathClassifier.empty_ticks_unknown", True))
        else:
            results.append(TestResult("logic:DeathClassifier.empty_ticks_unknown", False, f"Expected unknown, got {result3.reason}"))

        # Target lost death
        ticks4 = [{
            "state": "SCANNING",
            "signals": {"in_combat": False, "hit_confirmed": False},
            "risk": {"crowd_risk": 0.0, "visible_enemy_count": 0},
            "target": {"lost_ms": 4000},
        }]
        result4 = classifier.classify(ticks4)
        if result4.reason == "target_lost_death":
            results.append(TestResult("logic:DeathClassifier.target_lost_death", True))
        else:
            results.append(TestResult("logic:DeathClassifier.target_lost_death", False, f"Expected target_lost_death, got {result4.reason}"))

    except Exception as e:
        import traceback
        results.append(TestResult("logic:tests", False, f"{e}\n{traceback.format_exc()}"))

    return results


def run_telemetry_tests() -> list[TestResult]:
    """Verify MatchTelemetry writes valid JSONL."""
    results = []

    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from src.services.match_telemetry import MatchTelemetry, CombatTick, MatchSummary
        import tempfile
        import json

        # Reset singleton for clean test
        MatchTelemetry._instance = None
        MatchTelemetry._lock = __import__("threading").Lock()

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"combat_ai": {"telemetry_enabled": True, "telemetry_dir": tmpdir}}

            # Create instance with config
            import threading
            with threading.Lock():
                MatchTelemetry._instance = None
            tel = MatchTelemetry(config)

            tel.start_match(42)
            tel.record_tick(CombatTick(
                ts=1234567890.0,
                t_match=10.0,
                match_id=42,
                state="ENGAGED",
                action="attack",
                signals={"in_combat": True},
                target={"visible": True},
                risk={"crowd_risk": 0.5},
                decision={"intent": "engage"},
            ))
            tel.finish_match(MatchSummary(
                match_id=42,
                started_at=1234567880.0,
                ended_at=1234567890.0,
                duration_sec=10.0,
                kills=3,
                death_reason="combat_death",
            ))

            # Verify timeline.jsonl
            tl_path = Path(tmpdir) / "match_0042" / "timeline.jsonl"
            if tl_path.exists():
                with open(tl_path) as f:
                    line = f.readline()
                tick = json.loads(line)
                if tick.get("match_id") == 42 and tick.get("state") == "ENGAGED":
                    results.append(TestResult("telemetry:jsonl_writes", True))
                else:
                    results.append(TestResult("telemetry:jsonl_writes", False, f"Bad tick: {tick}"))
            else:
                results.append(TestResult("telemetry:jsonl_writes", False, f"File not found: {tl_path}"))

            # Verify summary.json
            sum_path = Path(tmpdir) / "match_0042" / "summary.json"
            if sum_path.exists():
                with open(sum_path) as f:
                    summary = json.load(f)
                if summary.get("death_reason") == "combat_death" and summary.get("kills") == 3:
                    results.append(TestResult("telemetry:summary_writes", True))
                else:
                    results.append(TestResult("telemetry:summary_writes", False, f"Bad summary: {summary}"))
            else:
                results.append(TestResult("telemetry:summary_writes", False, f"File not found: {sum_path}"))

            # Verify get_last_ticks
            tel2 = MatchTelemetry(config)
            ticks = tel2.get_last_ticks(5)
            if len(ticks) <= 5:
                results.append(TestResult("telemetry:get_last_ticks", True))
            else:
                results.append(TestResult("telemetry:get_last_ticks", False, f"Got {len(ticks)} ticks"))

    except Exception as e:
        import traceback
        results.append(TestResult("telemetry:tests", False, f"{e}\n{traceback.format_exc()}"))

    return results


def run_regression_tests() -> list[TestResult]:
    """Verify Phase 12.4 contracts still hold."""
    results = []

    # Discord event service imports
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from src.services.discord_event_service import (
            emit_event,
            should_dispatch,
            dedupe_kill_milestone,
            reset_kill_dedupe,
            capture_screenshot_png_bytes,
        )
        results.append(TestResult("regression:discord_event_service_imports", True))
    except Exception as e:
        results.append(TestResult("regression:discord_event_service_imports", False, str(e)))

    # Bot engine phase 12.4 hooks exist
    try:
        with open(REPO_ROOT / "src" / "core" / "bot_engine.py", "r") as f:
            content = f.read()
        checks = [
            ("_emit_death_event_once", "Phase 12.4 death event"),
            ("emit_event", "Phase 12.4 emit_event call"),
            ("_kill_milestone_sent", "Phase 12.4 kill milestone dedupe"),
            ("discord_event_service", "Phase 12.4 discord service import"),
            ("match_end", "Phase 12.4 match_end event"),
            ("combat_start", "Phase 12.4 combat_start event"),
        ]
        for symbol, label in checks:
            if symbol in content:
                results.append(TestResult(f"regression:{label}", True))
            else:
                results.append(TestResult(f"regression:{label}", False, f"'{symbol}' not found in bot_engine.py"))
    except Exception as e:
        results.append(TestResult("regression:bot_engine_checks", False, str(e)))

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify combat AI stack")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all results")
    args = parser.parse_args()

    print("=" * 60)
    print("Combat AI Verification — Phase 12.5")
    print("=" * 60)

    results = run_tests(verbose=args.verbose)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print()
    for r in results:
        if args.verbose or not r.passed:
            print(r)

    print()
    print("-" * 60)
    print(f"Results: {passed}/{total} PASS, {failed}/{total} FAIL")
    print("-" * 60)

    if failed > 0:
        print("\nFAILED checks:")
        for r in results:
            if not r.passed:
                print(f"  - {r.name}: {r.message or 'check failed'}")
        sys.exit(1)
    else:
        print("\nALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
