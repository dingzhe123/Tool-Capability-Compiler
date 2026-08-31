from __future__ import annotations

from ..core.errors import DuplicateToolError, RegistrationError, ToolNotFoundError
from ..core.tool import ToolNode


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolNode] = {}

    def register(self, node: ToolNode) -> None:
        if not isinstance(node, ToolNode):
            raise RegistrationError("Registered value must be a ToolNode")
        if node.spec.name in self._tools:
            raise DuplicateToolError(f"Tool already registered: {node.spec.name}")
        self._tools[node.spec.name] = node

    def get(self, name: str) -> ToolNode:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool not found: {name}") from exc

    def all(self) -> tuple[ToolNode, ...]:
        return tuple(self._tools[name] for name in sorted(self._tools))

    def in_layer(self, layer: str) -> tuple[ToolNode, ...]:
        return tuple(node for node in self.all() if node.spec.layer == layer)
