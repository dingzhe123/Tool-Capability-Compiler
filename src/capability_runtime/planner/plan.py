from __future__ import annotations

from dataclasses import dataclass

from ..core.artifact import ArtifactKey
from ..graph.models import DependencyEdge


@dataclass(frozen=True, slots=True)
class ExecutionNode:
    tool_name: str
    consumes: tuple[ArtifactKey, ...] = ()
    produces: tuple[ArtifactKey, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    nodes: tuple[ExecutionNode, ...]
    edges: tuple[DependencyEdge, ...]
    goal: ArtifactKey

    def explain(self) -> str:
        lines = ["Goal:", self.goal.name, "", "Selected tools:", ""]
        for index, node in enumerate(self.nodes, start=1):
            requires = ", ".join(item.name for item in node.consumes) or "(none)"
            produces = ", ".join(item.name for item in node.produces) or "(none)"
            lines.extend(
                [
                    f"{index}. {node.tool_name}",
                    f"   requires: {requires}",
                    f"   produces: {produces}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip()
