from __future__ import annotations

from ..core.errors import InvalidTopologyReferenceError, TopologyBuildError
from ..core.layer import Layer
from ..core.tool import NodeSelector, ToolNode
from ..registry import LayerRegistry, ToolRegistry
from .models import ToolEdge, Topology, TopologyValidationWarning


class TopologyBuilder:
    """Build adjacent-layer edges from the intersection of two allow-lists."""

    def __init__(self, layers: LayerRegistry, tools: ToolRegistry) -> None:
        self._layer_registry = layers
        self._tool_registry = tools

    def build(self) -> Topology:
        layers = self._layer_registry.all()
        self._validate_layer_order(layers)
        tools = self._tool_registry.all()
        nodes = {node.spec.name: node for node in tools}
        by_layer = {layer.name: self._tool_registry.in_layer(layer.name) for layer in layers}

        for node in tools:
            self._layer_registry.get(node.spec.layer)
        self._validate_references(layers, nodes)

        edges: list[ToolEdge] = []
        warnings: list[TopologyValidationWarning] = []
        for source_layer, target_layer in zip(layers, layers[1:], strict=False):
            for source in by_layer[source_layer.name]:
                for target in by_layer[target_layer.name]:
                    if not self._allows(source, target):
                        continue
                    edges.append(ToolEdge(source.spec.name, target.spec.name))
                    warning = self._schema_warning(source, target)
                    if warning is not None:
                        warnings.append(warning)
        return Topology(layers, nodes, tuple(edges), tuple(warnings))

    @staticmethod
    def _validate_layer_order(layers: tuple[Layer, ...]) -> None:
        for left, right in zip(layers, layers[1:], strict=False):
            if right.order != left.order + 1:
                raise TopologyBuildError(
                    f"Layer orders must be contiguous: {left.order} -> {right.order}"
                )

    @staticmethod
    def _allows(source: ToolNode, target: ToolNode) -> bool:
        return source.spec.workers.allows(target.spec.name) and target.spec.providers.allows(
            source.spec.name
        )

    def _validate_references(
        self, layers: tuple[Layer, ...], nodes: dict[str, ToolNode]
    ) -> None:
        layer_indexes = {layer.name: index for index, layer in enumerate(layers)}
        for node in nodes.values():
            index = layer_indexes[node.spec.layer]
            self._validate_selector(
                owner=node,
                selector=node.spec.providers,
                expected_layer=layers[index - 1].name if index > 0 else None,
                relation="provider",
                nodes=nodes,
            )
            self._validate_selector(
                owner=node,
                selector=node.spec.workers,
                expected_layer=layers[index + 1].name if index + 1 < len(layers) else None,
                relation="worker",
                nodes=nodes,
            )

    @staticmethod
    def _validate_selector(
        *,
        owner: ToolNode,
        selector: NodeSelector,
        expected_layer: str | None,
        relation: str,
        nodes: dict[str, ToolNode],
    ) -> None:
        if selector.all_nodes:
            return
        if expected_layer is None and selector.names:
            raise InvalidTopologyReferenceError(
                f"Tool {owner.spec.name} cannot declare {relation}s outside the topology"
            )
        for reference in sorted(selector.names):
            referenced = nodes.get(reference)
            if referenced is None:
                raise InvalidTopologyReferenceError(
                    f"Tool {owner.spec.name} references unknown {relation}: {reference}"
                )
            if referenced.spec.layer != expected_layer:
                raise InvalidTopologyReferenceError(
                    f"Tool {owner.spec.name} references {relation} {reference} in "
                    f"non-adjacent layer {referenced.spec.layer}"
                )

    @staticmethod
    def _schema_warning(
        source: ToolNode, target: ToolNode
    ) -> TopologyValidationWarning | None:
        if not source.spec.produces or not target.spec.consumes:
            return None
        if set(source.spec.produces).intersection(target.spec.consumes):
            return None
        source_types = ", ".join(item.__name__ for item in source.spec.produces)
        target_types = ", ".join(item.__name__ for item in target.spec.consumes)
        return TopologyValidationWarning(
            code="SCHEMA_MISMATCH",
            source=source.spec.name,
            target=target.spec.name,
            message=(
                f"Allowed edge {source.spec.name} -> {target.spec.name} has no exact "
                f"schema overlap ({source_types} -> {target_types})"
            ),
        )
