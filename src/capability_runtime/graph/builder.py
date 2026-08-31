from __future__ import annotations

import logging

from ..registry.tool_registry import ToolRegistry
from .models import DependencyEdge, DependencyGraph

logger = logging.getLogger(__name__)


class DependencyGraphBuilder:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def build(self) -> DependencyGraph:
        tools = self._registry.all()
        nodes = {registered_tool.spec.name: registered_tool for registered_tool in tools}
        edges: set[DependencyEdge] = set()
        for consumer in tools:
            for consumed in consumer.spec.consumes:
                for producer in self._registry.producers_of(consumed):
                    if producer.spec.name == consumer.spec.name:
                        continue
                    edges.add(
                        DependencyEdge(
                            source=producer.spec.name,
                            target=consumer.spec.name,
                            artifact=consumed,
                        )
                    )
        graph = DependencyGraph(self._registry, nodes, tuple(edges))
        logger.debug("graph built: %d nodes, %d edges", len(tools), len(edges))
        return graph
