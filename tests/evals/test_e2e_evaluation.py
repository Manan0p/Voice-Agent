import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from apps.agent.decision import DecisionEngine
from apps.agent.language.detector import LanguageDetector
from tests.fixtures.e2e_call_dataset import E2E_50_CALL_DATASET, E2ECallScenario


def run_e2e_benchmark() -> dict[str, Any]:
    """Run full 50-call evaluation benchmark and generate structured metrics."""
    detector = LanguageDetector()
    engine = DecisionEngine()

    results: list[dict[str, Any]] = []
    category_stats: dict[str, dict[str, int]] = {
        "recruiter": {"total": 0, "passed": 0},
        "delivery": {"total": 0, "passed": 0},
        "emergency": {"total": 0, "passed": 0},
        "spam": {"total": 0, "passed": 0},
        "friends": {"total": 0, "passed": 0},
    }

    latencies_ms: list[float] = []

    for scenario in E2E_50_CALL_DATASET:
        start_t = time.perf_counter()

        # 1. Detect Language
        lang_res = detector.analyze(scenario.utterance)

        # 2. Decision Engine Triage (resolves caller, classifies intent, urgency, and risk)
        decision = engine.evaluate(
            caller_id=scenario.caller_id,
            utterance=scenario.utterance,
            initial_name=scenario.initial_name,
        )

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Check Match
        intent_match = decision.intent.category == scenario.expected_intent
        urgency_match = decision.urgency.level == scenario.expected_urgency
        risk_match = decision.risk.level == scenario.expected_risk
        action_match = decision.recommended_action == scenario.expected_action

        # Overall Scenario Pass
        scenario_passed = intent_match and urgency_match and risk_match and action_match

        category_stats[scenario.category_group]["total"] += 1
        if scenario_passed:
            category_stats[scenario.category_group]["passed"] += 1

        results.append(
            {
                "id": scenario.id,
                "category": scenario.category_group,
                "description": scenario.scenario_description,
                "passed": scenario_passed,
                "latency_ms": round(elapsed_ms, 3),
                "expected": {
                    "intent": scenario.expected_intent.value,
                    "urgency": scenario.expected_urgency.value,
                    "risk": scenario.expected_risk.value,
                    "action": scenario.expected_action.value,
                },
                "actual": {
                    "intent": decision.intent.category.value,
                    "urgency": decision.urgency.level.value,
                    "risk": decision.risk.level.value,
                    "action": decision.recommended_action.value,
                    "detected_language": lang_res.style,
                },
            }
        )

    total_scenarios = len(E2E_50_CALL_DATASET)
    total_passed = sum(1 for r in results if r["passed"])
    overall_accuracy = (total_passed / total_scenarios) * 100.0 if total_scenarios else 0.0

    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
    p95_latency = sorted(latencies_ms)[int(len(latencies_ms) * 0.95)] if latencies_ms else 0.0

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_calls": total_scenarios,
        "total_passed": total_passed,
        "overall_accuracy_pct": round(overall_accuracy, 2),
        "target_pass_rate_pct": 95.0,
        "latency_benchmarks_ms": {
            "avg_ms": round(avg_latency, 3),
            "p95_ms": round(p95_latency, 3),
            "target_ms": 50.0,
        },
        "category_breakdown": {
            cat: {
                "total": stats["total"],
                "passed": stats["passed"],
                "accuracy_pct": round((stats["passed"] / stats["total"]) * 100.0, 2)
                if stats["total"]
                else 0.0,
            }
            for cat, stats in category_stats.items()
        },
        "call_evaluations": results,
    }

    # Save to eval_report.json
    output_path = Path("eval_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


@pytest.mark.parametrize("scenario", E2E_50_CALL_DATASET, ids=[s.id for s in E2E_50_CALL_DATASET])
def test_e2e_individual_scenario(scenario: E2ECallScenario) -> None:
    """Evaluate an individual simulated call scenario."""
    engine = DecisionEngine()

    # Decision Engine Triage
    decision = engine.evaluate(
        caller_id=scenario.caller_id,
        utterance=scenario.utterance,
        initial_name=scenario.initial_name,
    )

    assert decision.intent.category == scenario.expected_intent, (
        f"Intent mismatch on {scenario.id}: expected {scenario.expected_intent}, got {decision.intent.category}"
    )
    assert decision.urgency.level == scenario.expected_urgency, (
        f"Urgency mismatch on {scenario.id}: expected {scenario.expected_urgency}, got {decision.urgency.level}"
    )
    assert decision.risk.level == scenario.expected_risk, (
        f"Risk mismatch on {scenario.id}: expected {scenario.expected_risk}, got {decision.risk.level}"
    )
    assert decision.recommended_action == scenario.expected_action, (
        f"Action mismatch on {scenario.id}: expected {scenario.expected_action}, got {decision.recommended_action}"
    )


def test_e2e_benchmark_report_generation() -> None:
    """Verify that the aggregate benchmark generates eval_report.json with >95% accuracy."""
    report = run_e2e_benchmark()
    assert report["total_calls"] == 50
    assert report["overall_accuracy_pct"] >= 95.0
    assert report["latency_benchmarks_ms"]["p95_ms"] < 50.0
    assert os.path.exists("eval_report.json")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING 50-CALL END-TO-END BENCHMARK EVALUATION (Phase 11)")
    print("=" * 70)
    report = run_e2e_benchmark()
    print(f"Total Calls Evaluated: {report['total_calls']}")
    print(f"Total Passed:         {report['total_passed']}")
    print(f"Overall Accuracy:     {report['overall_accuracy_pct']}%")
    print(f"Average Latency:      {report['latency_benchmarks_ms']['avg_ms']} ms")
    print(f"P95 Latency:          {report['latency_benchmarks_ms']['p95_ms']} ms")
    print("-" * 70)
    print("CATEGORY BREAKDOWN:")
    for cat, stats in report["category_breakdown"].items():
        print(
            f"  • {cat.capitalize():<12}: {stats['passed']}/{stats['total']} ({stats['accuracy_pct']}%)"
        )
    print("=" * 70)
    print("Report saved to eval_report.json")
