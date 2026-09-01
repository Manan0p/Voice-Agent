"""Evaluation suite running 40+ simulated caller scenarios through the Decision Engine."""

import pytest

from apps.agent.decision.engine import DecisionEngine
from tests.fixtures.decision_dataset import DECISION_EVAL_DATASET, DecisionTestCase


@pytest.mark.parametrize("case", DECISION_EVAL_DATASET, ids=lambda c: c.id)
def test_decision_dataset_individual_cases(case: DecisionTestCase) -> None:
    """Evaluate decision triage for each scenario in the 40+ case dataset."""
    engine = DecisionEngine()
    decision = engine.evaluate(
        caller_id=case.caller_id,
        utterance=case.utterance,
        initial_name=case.initial_name,
    )

    assert decision.caller.relationship == case.expected_relationship, (
        f"Relationship mismatch for '{case.utterance}': got {decision.caller.relationship}, expected {case.expected_relationship}"
    )

    assert decision.intent.category == case.expected_intent, (
        f"Intent mismatch for '{case.utterance}': got {decision.intent.category}, expected {case.expected_intent}"
    )

    assert decision.urgency.level == case.expected_urgency, (
        f"Urgency mismatch for '{case.utterance}': got {decision.urgency.level}, expected {case.expected_urgency}"
    )

    assert decision.risk.level == case.expected_risk, (
        f"Risk mismatch for '{case.utterance}': got {decision.risk.level}, expected {case.expected_risk}"
    )

    assert decision.recommended_action == case.expected_action, (
        f"Action mismatch for '{case.utterance}': got {decision.recommended_action}, expected {case.expected_action}"
    )


def test_decision_dataset_aggregate_metrics() -> None:
    """Benchmark aggregate decision accuracy across all 40+ simulated caller scenarios."""
    engine = DecisionEngine()
    total_cases = len(DECISION_EVAL_DATASET)
    assert total_cases >= 35, f"Expected at least 35 test cases, found {total_cases}"

    correct_actions = 0
    correct_intents = 0
    correct_urgency = 0
    correct_risk = 0

    for case in DECISION_EVAL_DATASET:
        decision = engine.evaluate(
            caller_id=case.caller_id,
            utterance=case.utterance,
            initial_name=case.initial_name,
        )

        if decision.recommended_action == case.expected_action:
            correct_actions += 1
        if decision.intent.category == case.expected_intent:
            correct_intents += 1
        if decision.urgency.level == case.expected_urgency:
            correct_urgency += 1
        if decision.risk.level == case.expected_risk:
            correct_risk += 1

    action_acc = (correct_actions / total_cases) * 100.0
    intent_acc = (correct_intents / total_cases) * 100.0
    urgency_acc = (correct_urgency / total_cases) * 100.0
    risk_acc = (correct_risk / total_cases) * 100.0

    print(f"\n--- DECISION ENGINE BENCHMARK ({total_cases} scenarios) ---")
    print(f"Action Decision Accuracy: {action_acc:.1f}% ({correct_actions}/{total_cases})")
    print(f"Intent Category Accuracy:  {intent_acc:.1f}% ({correct_intents}/{total_cases})")
    print(f"Urgency Level Accuracy:    {urgency_acc:.1f}% ({correct_urgency}/{total_cases})")
    print(f"Risk Assessment Accuracy:  {risk_acc:.1f}% ({correct_risk}/{total_cases})")

    assert action_acc >= 95.0, f"Action accuracy too low: {action_acc}%"
    assert intent_acc >= 95.0, f"Intent accuracy too low: {intent_acc}%"
    assert urgency_acc >= 95.0, f"Urgency accuracy too low: {urgency_acc}%"
    assert risk_acc >= 95.0, f"Risk accuracy too low: {risk_acc}%"


if __name__ == "__main__":
    test_decision_dataset_aggregate_metrics()
