from dataclasses import dataclass, make_dataclass

import pytest

from capability_runtime import (
    CyclicDependencyError,
    DependencyGraphBuilder,
    Goal,
    MissingProducerError,
    Planner,
    ToolRegistry,
    UnsatisfiedDependencyError,
    tool,
)


def build_plan(tools, goal, inputs=()):
    registry = ToolRegistry()
    for item in tools:
        registry.register(item)
    graph = DependencyGraphBuilder(registry).build()
    return Planner(graph).plan(Goal.of(goal), set(inputs))


def test_linear_branch_and_pruning_are_deterministic() -> None:
    A = make_dataclass("A", [("value", int)], frozen=True)
    B = make_dataclass("B", [("value", int)], frozen=True)
    C = make_dataclass("C", [("value", int)], frozen=True)
    D = make_dataclass("D", [("value", int)], frozen=True)
    Noise = make_dataclass("Noise", [("value", int)], frozen=True)

    @tool(produces=[A])
    async def make_a(): return A(1)

    @tool(produces=[B])
    async def make_b(): return B(2)

    @tool(consumes=[A, B], produces=[C])
    async def combine(a, b): return C(a.value + b.value)

    @tool(consumes=[C], produces=[D])
    async def finish(c): return D(c.value)

    @tool(produces=[Noise])
    async def irrelevant(): return Noise(0)

    plan = build_plan((finish, irrelevant, make_b, combine, make_a), D)
    assert [node.tool_name for node in plan.nodes] == [
        "make_a",
        "make_b",
        "combine",
        "finish",
    ]
    assert "irrelevant" not in plan.explain()


def test_missing_producer() -> None:
    @dataclass(frozen=True)
    class Missing: pass

    @dataclass(frozen=True)
    class Result: pass

    @tool(consumes=[Missing], produces=[Result])
    async def finish(value): return Result()

    with pytest.raises(UnsatisfiedDependencyError) as error:
        build_plan((finish,), Result)
    assert isinstance(error.value.reasons[0], MissingProducerError)


def test_goal_without_any_producer_is_missing_producer() -> None:
    class Result: pass

    with pytest.raises(MissingProducerError):
        build_plan((), Result)


def test_cycle_reports_artifact_chain() -> None:
    class X: pass
    class Y: pass

    @tool(consumes=[Y], produces=[X])
    async def make_x(value): return X()

    @tool(consumes=[X], produces=[Y])
    async def make_y(value): return Y()

    with pytest.raises(CyclicDependencyError) as error:
        build_plan((make_x, make_y), X)
    assert [item.type_ for item in error.value.chain] == [X, Y, X]


def test_provider_priority_tie_and_unreachable_fallback() -> None:
    class Input: pass
    class Secret: pass
    class Result: pass

    @tool(name="z_high", consumes=[Secret], produces=[Result], priority=100)
    async def high(value): return Result()

    @tool(name="b_low", consumes=[Input], produces=[Result], priority=10)
    async def low(value): return Result()

    @tool(name="a_low", consumes=[Input], produces=[Result], priority=10)
    async def tied(value): return Result()

    plan = build_plan((high, low, tied), Result, (Input,))
    assert [node.tool_name for node in plan.nodes] == ["a_low"]
