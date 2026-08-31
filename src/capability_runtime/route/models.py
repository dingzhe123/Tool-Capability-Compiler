from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from ..core.errors import RouteValidationError
from ..topology import ToolEdge, Topology


@dataclass(frozen=True, slots=True)
class RouteLayer:
    layer: str
    tools: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoutePlan:
    """A topology-constrained subgraph; one layer may contain multiple tools."""

    layers: tuple[RouteLayer, ...]
    edges: tuple[ToolEdge, ...]

    @classmethod
    def from_groups(
        cls, topology: Topology, groups: Iterable[Iterable[str]]
    ) -> RoutePlan:
        normalized = [tuple(sorted(set(group))) for group in groups]
        if not normalized or any(not group for group in normalized):
            raise RouteValidationError("A route requires one or more non-empty layers")

        topology_layers = {layer.name: layer for layer in topology.layers()}
        route_layers: list[RouteLayer] = []
        for group in normalized:
            node_layers = {topology.node(name).spec.layer for name in group}
            if len(node_layers) != 1:
                raise RouteValidationError(
                    f"Tools in one route group must share a layer: {', '.join(group)}"
                )
            layer_name = next(iter(node_layers))
            route_layers.append(RouteLayer(layer_name, group))

        for left, right in zip(route_layers, route_layers[1:], strict=False):
            if topology_layers[right.layer].order != topology_layers[left.layer].order + 1:
                raise RouteValidationError(
                    f"Route layers must be adjacent: {left.layer} -> {right.layer}"
                )

        selected_edges: list[ToolEdge] = []
        for left, right in zip(route_layers, route_layers[1:], strict=False):
            pair_edges = [
                ToolEdge(source, target)
                for source in left.tools
                for target in right.tools
                if topology.has_edge(source, target)
            ]
            connected_sources = {edge.source for edge in pair_edges}
            connected_targets = {edge.target for edge in pair_edges}
            missing_sources = set(left.tools) - connected_sources
            missing_targets = set(right.tools) - connected_targets
            if missing_sources or missing_targets:
                raise RouteValidationError(
                    "Route contains disconnected tools; "
                    f"sources={sorted(missing_sources)}, targets={sorted(missing_targets)}"
                )
            selected_edges.extend(pair_edges)

        return cls(tuple(route_layers), tuple(selected_edges))

    def explain(self) -> str:
        return "\n  ↓\n".join(
            f"{layer.layer}: {{{', '.join(layer.tools)}}}" for layer in self.layers
        )
