from dataclasses import dataclass

from capability_runtime import (
    LayerRegistry,
    RoutePlan,
    ToolRegistry,
    TopologyBuilder,
    tool,
)


@dataclass(frozen=True)
class Order: pass


@dataclass(frozen=True)
class PolicyDocument: pass


@dataclass(frozen=True)
class RefundDecision: pass


@tool(layer="read", workers=["policy_check"], produces=[Order])
async def db(): return Order()


@tool(layer="read", workers=["policy_check"], produces=[PolicyDocument])
async def rag(): return PolicyDocument()


@tool(layer="read")
async def web_search(): return None


@tool(
    layer="analyze",
    providers=["db", "rag"],
    workers=["refund"],
    consumes=[Order, PolicyDocument],
    produces=[RefundDecision],
)
async def policy_check(order, document): return RefundDecision()


@tool(layer="analyze", workers=[])
async def summarizer(): return None


@tool(layer="act", providers=["policy_check"], consumes=[RefundDecision])
async def refund(decision): return None


@tool(layer="act", providers=[])
async def send_email(): return None


def test_refund_declared_topology_and_route() -> None:
    layers = LayerRegistry()
    for order, name in enumerate(("read", "analyze", "act")):
        layers.register(name, order)
    tools = ToolRegistry()
    for node in (db, rag, web_search, policy_check, summarizer, refund, send_email):
        tools.register(node)

    topology = TopologyBuilder(layers, tools).build()
    assert {(edge.source, edge.target) for edge in topology.edges()} == {
        ("db", "policy_check"),
        ("rag", "policy_check"),
        ("policy_check", "refund"),
        ("web_search", "summarizer"),
    }
    route = RoutePlan.from_groups(
        topology, [{"db", "rag"}, {"policy_check"}, {"refund"}]
    )
    assert len(route.layers) == 3
    assert topology.warnings() == ()
