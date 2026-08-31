import asyncio
from dataclasses import dataclass

from capability_runtime import (
    DependencyGraphBuilder,
    Goal,
    Planner,
    Runtime,
    ToolRegistry,
    tool,
)


@dataclass(frozen=True)
class OrderId:
    value: str


@dataclass(frozen=True)
class PolicyId:
    value: str


@dataclass(frozen=True)
class Order:
    id: str
    amount: float


@dataclass(frozen=True)
class RefundPolicy:
    max_amount: float


@dataclass(frozen=True)
class RefundDecision:
    allowed: bool


@dataclass(frozen=True)
class RefundResult:
    success: bool


class User: pass
class EmailResult: pass


@tool(consumes=[OrderId], produces=[Order])
async def get_order(order_id): return Order(order_id.value, 50.0)


@tool(consumes=[PolicyId], produces=[RefundPolicy])
async def get_refund_policy(policy_id): return RefundPolicy(100.0)


@tool(consumes=[Order, RefundPolicy], produces=[RefundDecision])
async def check_refund(order, policy):
    return RefundDecision(order.amount <= policy.max_amount)


@tool(consumes=[Order, RefundDecision], produces=[RefundResult])
async def refund_order(order, decision): return RefundResult(decision.allowed)


@tool(produces=[User])
async def get_user(): return User()


@tool(consumes=[User], produces=[EmailResult])
async def send_email(user): return EmailResult()


def test_refund_plan_is_minimal_and_executes() -> None:
    registry = ToolRegistry()
    for item in (
        send_email,
        refund_order,
        get_user,
        check_refund,
        get_refund_policy,
        get_order,
    ):
        registry.register(item)
    graph = DependencyGraphBuilder(registry).build()
    plan = Planner(graph).plan(Goal.of(RefundResult), {OrderId, PolicyId})

    assert [node.tool_name for node in plan.nodes] == [
        "get_order",
        "get_refund_policy",
        "check_refund",
        "refund_order",
    ]
    result = asyncio.run(
        Runtime(registry).execute(
            plan,
            {OrderId: OrderId("001"), PolicyId: PolicyId("default")},
        )
    )
    assert result == RefundResult(success=True)
