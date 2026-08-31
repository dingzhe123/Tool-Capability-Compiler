from dataclasses import dataclass

from capability_runtime import LayerRegistry, RoutePlan, ToolRegistry, TopologyBuilder, tool


@dataclass(frozen=True)
class Order:
    id: str


@dataclass(frozen=True)
class Decision:
    allowed: bool


@tool(layer="read", workers=["policy_check"], produces=[Order])
async def database() -> Order:
    return Order("123")


@tool(
    layer="analyze",
    providers=["database"],
    workers=["refund"],
    consumes=[Order],
    produces=[Decision],
)
async def policy_check(order: Order) -> Decision:
    return Decision(allowed=True)


@tool(layer="act", providers=["policy_check"], consumes=[Decision])
async def refund(decision: Decision) -> None:
    return None


def main() -> None:
    layers = LayerRegistry()
    layers.register("read", 0)
    layers.register("analyze", 1)
    layers.register("act", 2)

    tools = ToolRegistry()
    for node in (database, policy_check, refund):
        tools.register(node)

    topology = TopologyBuilder(layers, tools).build()
    route = RoutePlan.from_groups(
        topology, [{"database"}, {"policy_check"}, {"refund"}]
    )
    print(route.explain())


if __name__ == "__main__":
    main()
