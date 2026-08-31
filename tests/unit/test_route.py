import pytest

from capability_runtime import (
    LayerRegistry,
    RoutePlan,
    RouteValidationError,
    ToolRegistry,
    TopologyBuilder,
    tool,
)


def topology_for_route():
    layers = LayerRegistry()
    layers.register("read", 0)
    layers.register("analyze", 1)
    layers.register("act", 2)

    @tool(layer="read")
    async def db(): return None

    @tool(layer="read")
    async def rag(): return None

    @tool(layer="analyze", workers=["refund"])
    async def policy(): return None

    @tool(layer="analyze", workers=[])
    async def summary(): return None

    @tool(layer="act", providers=["policy"])
    async def refund(): return None

    tools = ToolRegistry()
    for node in (db, rag, policy, summary, refund):
        tools.register(node)
    return TopologyBuilder(layers, tools).build()


def test_route_supports_multiple_tools_in_one_layer() -> None:
    route = RoutePlan.from_groups(
        topology_for_route(), [{"rag", "db"}, {"policy"}, {"refund"}]
    )
    assert route.layers[0].tools == ("db", "rag")
    assert "read: {db, rag}" in route.explain()


def test_route_rejects_disconnected_selected_tools() -> None:
    with pytest.raises(RouteValidationError):
        RoutePlan.from_groups(
            topology_for_route(), [{"db"}, {"policy", "summary"}, {"refund"}]
        )
