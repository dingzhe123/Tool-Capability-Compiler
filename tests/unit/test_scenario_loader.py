import json

import pytest

from capability_runtime import ScenarioLoader, ScenarioValidationError


def valid_suite() -> dict:
    return {
        "version": "1.0",
        "name": "refund-regression",
        "description": "Refund coverage scenarios",
        "scenarios": [
            {
                "id": "refund_001",
                "query": "Can order 123 be refunded?",
                "category": "refund",
                "expected_capabilities": [
                    "order.read",
                    "refund.policy.check",
                ],
                "metadata": {"priority": "high", "attempts": 3},
            },
            {
                "id": "refund_002",
                "query": "Can I still return this order?",
            },
        ],
    }


def test_loads_gold_and_query_only_scenarios() -> None:
    suite = ScenarioLoader().load_data(valid_suite())

    assert suite.name == "refund-regression"
    assert suite.version == "1.0"
    assert suite.scenarios[0].is_gold
    assert suite.scenarios[0].metadata["priority"] == "high"
    assert not suite.scenarios[1].is_gold
    assert suite.scenarios[1].expected_capabilities == ()


def test_load_file_reads_utf8_json(tmp_path) -> None:
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(valid_suite(), ensure_ascii=False), encoding="utf-8")
    suite = ScenarioLoader().load_file(path)
    assert len(suite.scenarios) == 2


def test_duplicate_scenario_ids_are_rejected() -> None:
    data = valid_suite()
    data["scenarios"][1]["id"] = "refund_001"
    with pytest.raises(ScenarioValidationError, match="Duplicate scenario ids"):
        ScenarioLoader().load_data(data)


def test_missing_or_empty_query_is_rejected() -> None:
    data = valid_suite()
    del data["scenarios"][0]["query"]
    with pytest.raises(ScenarioValidationError, match="missing required fields"):
        ScenarioLoader().load_data(data)

    data = valid_suite()
    data["scenarios"][0]["query"] = "   "
    with pytest.raises(ScenarioValidationError, match="query"):
        ScenarioLoader().load_data(data)


def test_invalid_capabilities_and_metadata_are_rejected() -> None:
    data = valid_suite()
    data["scenarios"][0]["expected_capabilities"] = ["RefundCheck"]
    with pytest.raises(ScenarioValidationError, match="invalid capability"):
        ScenarioLoader().load_data(data)

    data = valid_suite()
    data["scenarios"][0]["metadata"] = []
    with pytest.raises(ScenarioValidationError, match="metadata"):
        ScenarioLoader().load_data(data)


def test_empty_suite_and_unknown_fields_are_rejected() -> None:
    data = valid_suite()
    data["scenarios"] = []
    with pytest.raises(ScenarioValidationError, match="cannot be empty"):
        ScenarioLoader().load_data(data)

    data = valid_suite()
    data["unexpected"] = True
    with pytest.raises(ScenarioValidationError, match="unknown fields"):
        ScenarioLoader().load_data(data)


def test_invalid_json_is_reported_as_validation_error(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ScenarioValidationError, match="Invalid scenario JSON"):
        ScenarioLoader().load_file(path)
