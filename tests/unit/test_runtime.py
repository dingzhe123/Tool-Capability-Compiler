import asyncio
from dataclasses import dataclass

import pytest

from capability_runtime import (
    ArtifactConflictError,
    ArtifactKey,
    DependencyGraphBuilder,
    Goal,
    InvalidToolOutputError,
    MissingRuntimeInputError,
    Planner,
    Runtime,
    ToolExecutionError,
    ToolRegistry,
    tool,
)
from capability_runtime.planner import ExecutionNode, ExecutionPlan


@dataclass(frozen=True)
class Input:
    value: int


@dataclass(frozen=True)
class Intermediate:
    value: int


@dataclass(frozen=True)
class Result:
    value: int


def setup(*tools):
    registry = ToolRegistry()
    for item in tools:
        registry.register(item)
    return registry, DependencyGraphBuilder(registry).build()


def test_input_injection_propagation_and_goal_result() -> None:
    @tool(consumes=[Input], produces=[Intermediate])
    async def increment(value): return Intermediate(value.value + 1)

    @tool(consumes=[Input, Intermediate], produces=[Result])
    async def add(original, changed): return Result(original.value + changed.value)

    registry, graph = setup(increment, add)
    plan = Planner(graph).plan(Goal.of(Result), {Input})
    result = asyncio.run(Runtime(registry).execute(plan, {Input: Input(2)}))
    assert result == Result(5)


def test_missing_runtime_input_fails_without_replanning() -> None:
    @tool(consumes=[Input], produces=[Result])
    async def finish(value): return Result(value.value)

    registry, graph = setup(finish)
    plan = Planner(graph).plan(Goal.of(Result), {Input})
    with pytest.raises(MissingRuntimeInputError):
        asyncio.run(Runtime(registry).execute(plan))


def test_invalid_output_type_is_rejected() -> None:
    @tool(produces=[Result])
    async def broken(): return "not a result"

    registry, graph = setup(broken)
    plan = Planner(graph).plan(Goal.of(Result))
    with pytest.raises(InvalidToolOutputError):
        asyncio.run(Runtime(registry).execute(plan))


def test_tool_exception_is_chained() -> None:
    @tool(produces=[Result])
    async def broken():
        raise ValueError("boom")

    registry, graph = setup(broken)
    plan = Planner(graph).plan(Goal.of(Result))
    with pytest.raises(ToolExecutionError) as error:
        asyncio.run(Runtime(registry).execute(plan))
    assert isinstance(error.value.__cause__, ValueError)


def test_initial_input_type_is_validated() -> None:
    @tool(consumes=[Input], produces=[Result])
    async def finish(value): return Result(value.value)

    registry, graph = setup(finish)
    plan = Planner(graph).plan(Goal.of(Result), {Input})
    with pytest.raises(InvalidToolOutputError):
        asyncio.run(
            Runtime(registry).execute(plan, {ArtifactKey.of(Input): "wrong"})
        )


def test_plan_with_two_producers_for_one_artifact_is_rejected() -> None:
    @tool(name="first", produces=[Result])
    async def first(): return Result(1)

    @tool(name="second", produces=[Result])
    async def second(): return Result(2)

    registry, _ = setup(first, second)
    key = ArtifactKey.of(Result)
    plan = ExecutionPlan(
        nodes=(
            ExecutionNode("first", produces=(key,)),
            ExecutionNode("second", produces=(key,)),
        ),
        edges=(),
        goal=key,
    )
    with pytest.raises(ArtifactConflictError):
        asyncio.run(Runtime(registry).execute(plan))
