import pytest

from capability_runtime import (
    DuplicateLayerError,
    DuplicateToolError,
    LayerRegistry,
    ToolRegistry,
    tool,
)


@tool(layer="read")
async def reader():
    return None


def test_layer_registry_is_ordered_and_unique() -> None:
    layers = LayerRegistry()
    layers.register("analyze", 1)
    layers.register("read", 0)
    assert [layer.name for layer in layers.all()] == ["read", "analyze"]

    with pytest.raises(DuplicateLayerError):
        layers.register("read", 2)
    with pytest.raises(DuplicateLayerError):
        layers.register("other", 1)


def test_tool_registry_is_deterministic_and_unique() -> None:
    tools = ToolRegistry()
    tools.register(reader)
    assert tools.get("reader") is reader
    assert tools.in_layer("read") == (reader,)

    with pytest.raises(DuplicateToolError):
        tools.register(reader)
