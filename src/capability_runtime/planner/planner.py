from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field

from ..core.artifact import ArtifactKey, ArtifactLike, artifact_key
from ..core.errors import (
    ArtifactConflictError,
    CyclicDependencyError,
    GraphRuntimeError,
    InvalidExecutionPlanError,
    MissingProducerError,
    UnsatisfiedDependencyError,
)
from ..core.tool import Tool
from ..graph.models import DependencyEdge, DependencyGraph
from ..registry.tool_registry import ToolRegistry
from .goal import Goal
from .plan import ExecutionNode, ExecutionPlan

logger = logging.getLogger(__name__)


@dataclass
class _PlanningState:
    selected: dict[str, Tool] = field(default_factory=dict)
    resolved: set[ArtifactKey] = field(default_factory=set)
    producers: dict[ArtifactKey, str] = field(default_factory=dict)

    def clone(self) -> _PlanningState:
        return _PlanningState(
            selected=dict(self.selected),
            resolved=set(self.resolved),
            producers=dict(self.producers),
        )


class Planner:
    def __init__(
        self,
        graph: DependencyGraph,
        *,
        registry: ToolRegistry | None = None,
    ) -> None:
        self._graph = graph
        self._registry = registry or graph.registry

    def plan(
        self,
        goal: Goal,
        available_inputs: set[ArtifactLike] | None = None,
    ) -> ExecutionPlan:
        available = {artifact_key(item) for item in (available_inputs or set())}
        state = _PlanningState(resolved=set(available))
        logger.debug("planning started: %s", goal.produces)
        state = self._resolve(goal.produces, state, ())
        edges = self._selected_edges(state.selected)
        ordered_names = self._topological_sort(state.selected, edges)
        nodes = tuple(
            ExecutionNode(
                tool_name=name,
                consumes=self._registry.get(name).spec.consumes,
                produces=self._registry.get(name).spec.produces,
            )
            for name in ordered_names
        )
        return ExecutionPlan(nodes=nodes, edges=edges, goal=goal.produces)

    def _resolve(
        self,
        artifact: ArtifactKey,
        state: _PlanningState,
        stack: tuple[ArtifactKey, ...],
    ) -> _PlanningState:
        if artifact in state.resolved:
            return state
        if artifact in stack:
            start = stack.index(artifact)
            raise CyclicDependencyError((*stack[start:], artifact))

        candidates = self._registry.producers_of(artifact)
        if not candidates:
            raise MissingProducerError(artifact)

        failures: list[GraphRuntimeError] = []
        for producer in candidates:
            candidate_state = state.clone()
            try:
                self._select(producer, candidate_state)
                for dependency in producer.spec.consumes:
                    candidate_state = self._resolve(
                        dependency, candidate_state, (*stack, artifact)
                    )
                candidate_state.resolved.update(producer.spec.produces)
                logger.debug(
                    "provider selected: %s for %s", producer.spec.name, artifact
                )
                return candidate_state
            except GraphRuntimeError as exc:
                failures.append(exc)

        cycles = [failure for failure in failures if isinstance(failure, CyclicDependencyError)]
        if cycles and len(cycles) == len(failures):
            raise cycles[0]
        raise UnsatisfiedDependencyError(artifact, failures)

    @staticmethod
    def _select(producer: Tool, state: _PlanningState) -> None:
        if producer.spec.name in state.selected:
            return
        for produced in producer.spec.produces:
            existing = state.producers.get(produced)
            if existing is not None and existing != producer.spec.name:
                raise ArtifactConflictError(produced, (existing, producer.spec.name))
        state.selected[producer.spec.name] = producer
        for produced in producer.spec.produces:
            state.producers[produced] = producer.spec.name

    def _selected_edges(
        self, selected: dict[str, Tool]
    ) -> tuple[DependencyEdge, ...]:
        names = set(selected)
        return tuple(
            edge
            for edge in self._graph.edges()
            if edge.source in names and edge.target in names
        )

    @staticmethod
    def _topological_sort(
        selected: dict[str, Tool], edges: tuple[DependencyEdge, ...]
    ) -> tuple[str, ...]:
        indegree = {name: 0 for name in selected}
        outgoing: dict[str, set[str]] = {name: set() for name in selected}
        for edge in edges:
            if edge.target not in outgoing[edge.source]:
                outgoing[edge.source].add(edge.target)
                indegree[edge.target] += 1
        ready = [name for name, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        ordered: list[str] = []
        while ready:
            name = heapq.heappop(ready)
            ordered.append(name)
            for target in sorted(outgoing[name]):
                indegree[target] -= 1
                if indegree[target] == 0:
                    heapq.heappush(ready, target)
        if len(ordered) != len(selected):
            raise InvalidExecutionPlanError("Selected tool graph contains a cycle")
        return tuple(ordered)
