from __future__ import annotations

from dataclasses import dataclass

from ..core.artifact import ArtifactKey
from ..core.errors import ToolNotFoundError
from ..core.tool import Tool
from ..registry.tool_registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    source: str
    target: str
    artifact: ArtifactKey


class DependencyGraph:
    def __init__(
        self,
        registry: ToolRegistry,
        nodes: dict[str, Tool],
        edges: tuple[DependencyEdge, ...],
    ) -> None:
        self.registry = registry
        self._nodes = dict(nodes)
        self._edges = tuple(
            sorted(edges, key=lambda edge: (edge.source, edge.target, edge.artifact.name))
        )
        self._incoming: dict[str, list[DependencyEdge]] = {
            name: [] for name in self._nodes
        }
        self._outgoing: dict[str, list[DependencyEdge]] = {
            name: [] for name in self._nodes
        }
        for edge in self._edges:
            self._incoming[edge.target].append(edge)
            self._outgoing[edge.source].append(edge)

    def nodes(self) -> tuple[str, ...]:
        return tuple(sorted(self._nodes))

    def edges(self) -> tuple[DependencyEdge, ...]:
        return self._edges

    def tool(self, name: str) -> Tool:
        try:
            return self._nodes[name]
        except KeyError as exc:
            raise ToolNotFoundError(name) from exc

    def predecessors(self, tool_name: str) -> tuple[str, ...]:
        self.tool(tool_name)
        return tuple(sorted({edge.source for edge in self._incoming[tool_name]}))

    def successors(self, tool_name: str) -> tuple[str, ...]:
        self.tool(tool_name)
        return tuple(sorted({edge.target for edge in self._outgoing[tool_name]}))
