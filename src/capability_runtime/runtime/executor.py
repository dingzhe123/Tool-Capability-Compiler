from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from ..core.artifact import ArtifactKey, ArtifactLike, artifact_key
from ..core.errors import (
    ArtifactConflictError,
    InvalidExecutionPlanError,
    InvalidToolOutputError,
    MissingRuntimeInputError,
    ToolExecutionError,
)
from ..planner.plan import ExecutionPlan
from ..registry.tool_registry import ToolRegistry
from .state import ExecutionState

logger = logging.getLogger(__name__)


class Runtime:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def execute(
        self,
        plan: ExecutionPlan,
        inputs: Mapping[ArtifactLike, Any] | None = None,
    ) -> Any:
        self._validate_plan(plan)
        normalized_inputs = {
            artifact_key(key): value for key, value in (inputs or {}).items()
        }
        self._validate_initial_values(normalized_inputs)
        state = ExecutionState(normalized_inputs)

        for node in plan.nodes:
            registered_tool = self._registry.get(node.tool_name)
            tool_inputs: dict[ArtifactKey, Any] = {}
            for required in registered_tool.spec.consumes:
                if not state.contains(required):
                    raise MissingRuntimeInputError(node.tool_name, required)
                tool_inputs[required] = state.get(required)
            logger.debug("tool execution started: %s", node.tool_name)
            try:
                outputs = await registered_tool.execute(tool_inputs)
            except Exception as exc:
                if isinstance(exc, (MissingRuntimeInputError, InvalidToolOutputError)):
                    raise
                raise ToolExecutionError(node.tool_name) from exc
            self._validate_outputs(node.tool_name, registered_tool.spec.produces, outputs)
            state.update(outputs)
            logger.debug("tool execution completed: %s", node.tool_name)

        if not state.contains(plan.goal):
            raise InvalidExecutionPlanError(
                f"Execution completed without producing goal: {plan.goal}"
            )
        return state.get(plan.goal)

    @staticmethod
    def _validate_initial_values(inputs: Mapping[ArtifactKey, Any]) -> None:
        for key, value in inputs.items():
            if type(value) is not key.type_:
                raise InvalidToolOutputError(
                    "<inputs>",
                    f"{key} expected {key.type_.__name__}, got {type(value).__name__}",
                )

    def _validate_plan(self, plan: ExecutionPlan) -> None:
        names = [node.tool_name for node in plan.nodes]
        if len(names) != len(set(names)):
            raise InvalidExecutionPlanError("Execution plan contains duplicate tools")
        positions = {name: index for index, name in enumerate(names)}
        produced_by: dict[ArtifactKey, str] = {}
        for node in plan.nodes:
            registered_tool = self._registry.get(node.tool_name)
            if (
                node.consumes != registered_tool.spec.consumes
                or node.produces != registered_tool.spec.produces
            ):
                raise InvalidExecutionPlanError(
                    f"Execution node metadata does not match registry: {node.tool_name}"
                )
            for produced in registered_tool.spec.produces:
                existing = produced_by.get(produced)
                if existing is not None:
                    raise ArtifactConflictError(produced, (existing, node.tool_name))
                produced_by[produced] = node.tool_name
        for edge in plan.edges:
            if edge.source not in positions or edge.target not in positions:
                raise InvalidExecutionPlanError("Execution edge references an unknown tool")
            if positions[edge.source] >= positions[edge.target]:
                raise InvalidExecutionPlanError(
                    f"Execution nodes are not topological for edge "
                    f"{edge.source} -> {edge.target}"
                )

    @staticmethod
    def _validate_outputs(
        tool_name: str,
        expected: tuple[ArtifactKey, ...],
        outputs: object,
    ) -> None:
        if not isinstance(outputs, dict):
            raise InvalidToolOutputError(tool_name, "execute() must return a dict")
        actual_keys = set(outputs)
        expected_keys = set(expected)
        if actual_keys != expected_keys:
            missing = sorted(key.name for key in expected_keys - actual_keys)
            extra = sorted(
                getattr(key, "name", repr(key)) for key in actual_keys - expected_keys
            )
            raise InvalidToolOutputError(
                tool_name, f"output keys differ; missing={missing}, extra={extra}"
            )
        for key in expected:
            value = outputs[key]
            if type(value) is not key.type_:
                raise InvalidToolOutputError(
                    tool_name,
                    f"{key} expected {key.type_.__name__}, got {type(value).__name__}",
                )
