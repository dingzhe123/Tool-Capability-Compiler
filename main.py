import asyncio
from dataclasses import dataclass

from capability_runtime import (
    ArtifactKey,
    DependencyGraphBuilder,
    Goal,
    Planner,
    Runtime,
    ToolRegistry,
    tool,
)


@dataclass(frozen=True)
class Input:
    value: int


@dataclass(frozen=True)
class Result:
    value: int


@tool(consumes=[Input], produces=[Result])
async def double(value: Input) -> Result:
    return Result(value.value * 2)


async def run_demo() -> None:
    registry = ToolRegistry()
    registry.register(double)
    graph = DependencyGraphBuilder(registry).build()
    plan = Planner(graph).plan(Goal.of(Result), {Input})
    print(plan.explain())
    result = await Runtime(registry).execute(
        plan, {ArtifactKey.of(Input): Input(21)}
    )
    print(f"\nResult: {result.value}")


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
