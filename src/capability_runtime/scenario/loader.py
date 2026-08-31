from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..core.errors import ScenarioLoadError, ScenarioValidationError
from .models import Scenario, ScenarioSuite

_SUITE_FIELDS = {"name", "version", "description", "scenarios"}
_SCENARIO_FIELDS = {
    "id",
    "query",
    "category",
    "expected_capabilities",
    "metadata",
}


class ScenarioLoader:
    def load_file(self, path: str | Path) -> ScenarioSuite:
        source = Path(path)
        try:
            raw = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise ScenarioLoadError(f"Cannot read scenario file: {source}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ScenarioValidationError(
                f"Invalid scenario JSON at line {exc.lineno}, column {exc.colno}"
            ) from exc
        return self.load_data(data)

    def load_data(self, data: object) -> ScenarioSuite:
        suite = self._require_mapping(data, "Scenario suite")
        self._reject_unknown_fields(suite, _SUITE_FIELDS, "Scenario suite")
        self._require_fields(suite, {"name", "version", "scenarios"}, "Scenario suite")

        raw_scenarios = suite["scenarios"]
        if not isinstance(raw_scenarios, list):
            raise ScenarioValidationError("Scenario suite 'scenarios' must be a list")

        scenarios = tuple(
            self._parse_scenario(item, index)
            for index, item in enumerate(raw_scenarios)
        )
        return ScenarioSuite(
            name=suite["name"],
            version=suite["version"],
            description=suite.get("description", ""),
            scenarios=scenarios,
        )

    def _parse_scenario(self, data: object, index: int) -> Scenario:
        location = f"Scenario at index {index}"
        item = self._require_mapping(data, location)
        self._reject_unknown_fields(item, _SCENARIO_FIELDS, location)
        self._require_fields(item, {"id", "query"}, location)

        capabilities = item.get("expected_capabilities", [])
        if not isinstance(capabilities, list) or any(
            not isinstance(value, str) for value in capabilities
        ):
            raise ScenarioValidationError(
                f"{location} 'expected_capabilities' must be a list of strings"
            )
        metadata = item.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ScenarioValidationError(f"{location} 'metadata' must be an object")

        return Scenario(
            id=item["id"],
            query=item["query"],
            category=item.get("category"),
            expected_capabilities=tuple(capabilities),
            metadata=dict(metadata),
        )

    @staticmethod
    def _require_mapping(value: object, location: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise ScenarioValidationError(f"{location} must be a JSON object")
        return value

    @staticmethod
    def _require_fields(
        value: Mapping[str, Any], required: set[str], location: str
    ) -> None:
        missing = sorted(required - set(value))
        if missing:
            raise ScenarioValidationError(
                f"{location} is missing required fields: {', '.join(missing)}"
            )

    @staticmethod
    def _reject_unknown_fields(
        value: Mapping[str, Any], allowed: set[str], location: str
    ) -> None:
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ScenarioValidationError(
                f"{location} has unknown fields: {', '.join(unknown)}"
            )
