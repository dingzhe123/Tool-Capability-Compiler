from __future__ import annotations

from ..core.capability import validate_capability_name
from ..core.errors import RegistrationError
from ..core.tool import ToolNode
from .tool_registry import ToolRegistry


class CapabilityRegistry:
    """A deterministic many-to-many index between capabilities and tools."""

    def __init__(self) -> None:
        self._providers: dict[str, set[str]] = {}
        self._by_tool: dict[str, set[str]] = {}

    def register(self, capability: str, tool_name: str) -> None:
        canonical = validate_capability_name(capability)
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise RegistrationError("Tool name must be a non-empty string")
        self._providers.setdefault(canonical, set()).add(tool_name)
        self._by_tool.setdefault(tool_name, set()).add(canonical)

    def register_tool(self, node: ToolNode) -> None:
        for capability in sorted(node.spec.capabilities):
            self.register(capability, node.spec.name)

    @classmethod
    def from_tools(cls, tools: ToolRegistry) -> CapabilityRegistry:
        registry = cls()
        for node in tools.all():
            registry.register_tool(node)
        return registry

    def providers(self, capability: str) -> tuple[str, ...]:
        canonical = validate_capability_name(capability)
        return tuple(sorted(self._providers.get(canonical, ())))

    def capabilities_of(self, tool_name: str) -> frozenset[str]:
        return frozenset(self._by_tool.get(tool_name, ()))

    def all(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))
