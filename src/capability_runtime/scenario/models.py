from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..core.capability import validate_capability_name
from ..core.errors import InvalidCapabilityError, ScenarioValidationError


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    query: str
    category: str | None = None
    expected_capabilities: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ScenarioValidationError("Scenario id must be a non-empty string")
        if not isinstance(self.query, str) or not self.query.strip():
            raise ScenarioValidationError(
                f"Scenario {self.id!r} query must be a non-empty string"
            )
        if self.category is not None and (
            not isinstance(self.category, str) or not self.category.strip()
        ):
            raise ScenarioValidationError(
                f"Scenario {self.id!r} category must be a non-empty string or null"
            )

        capabilities = tuple(self.expected_capabilities)
        if len(capabilities) != len(set(capabilities)):
            raise ScenarioValidationError(
                f"Scenario {self.id!r} has duplicate expected capabilities"
            )
        for capability in capabilities:
            try:
                validate_capability_name(capability)
            except InvalidCapabilityError as exc:
                raise ScenarioValidationError(
                    f"Scenario {self.id!r} has invalid capability: {capability!r}"
                ) from exc

        if not isinstance(self.metadata, Mapping):
            raise ScenarioValidationError(
                f"Scenario {self.id!r} metadata must be a JSON object"
            )
        metadata = copy.deepcopy(dict(self.metadata))
        try:
            json.dumps(metadata)
        except (TypeError, ValueError) as exc:
            raise ScenarioValidationError(
                f"Scenario {self.id!r} metadata must be JSON serializable"
            ) from exc

        object.__setattr__(self, "id", self.id.strip())
        object.__setattr__(self, "query", self.query.strip())
        object.__setattr__(
            self, "category", self.category.strip() if self.category is not None else None
        )
        object.__setattr__(self, "expected_capabilities", capabilities)
        object.__setattr__(self, "metadata", metadata)

    @property
    def is_gold(self) -> bool:
        return bool(self.expected_capabilities)


@dataclass(frozen=True, slots=True)
class ScenarioSuite:
    name: str
    version: str
    scenarios: tuple[Scenario, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ScenarioValidationError("Scenario suite name must be a non-empty string")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ScenarioValidationError(
                "Scenario suite version must be a non-empty string"
            )
        if not isinstance(self.description, str):
            raise ScenarioValidationError("Scenario suite description must be a string")
        scenarios = tuple(self.scenarios)
        if not scenarios:
            raise ScenarioValidationError("Scenario suite cannot be empty")
        if any(not isinstance(scenario, Scenario) for scenario in scenarios):
            raise ScenarioValidationError(
                "Scenario suite entries must be Scenario instances"
            )
        identifiers = [scenario.id for scenario in scenarios]
        duplicates = sorted(
            identifier for identifier in set(identifiers) if identifiers.count(identifier) > 1
        )
        if duplicates:
            raise ScenarioValidationError(
                f"Duplicate scenario ids: {', '.join(duplicates)}"
            )
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "version", self.version.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "scenarios", scenarios)
