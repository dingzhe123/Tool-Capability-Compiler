from dataclasses import dataclass

from capability_runtime import DependencyGraphBuilder, ToolRegistry, tool


@dataclass(frozen=True)
class X:
    value: int


@dataclass(frozen=True)
class Y:
    value: int


@tool(produces=[X])
async def a() -> X:
    return X(1)


@tool(consumes=[X], produces=[Y])
async def b(value: X) -> Y:
    return Y(value.value)


@tool(consumes=[X], produces=[str])
async def c(value: X) -> str:
    return str(value.value)


@tool(consumes=[X], produces=[X])
async def normalize(value: X) -> X:
    return value


def test_builds_exact_type_edges_and_inspection() -> None:
    registry = ToolRegistry()
    for item in (a, b, c, normalize):
        registry.register(item)
    graph = DependencyGraphBuilder(registry).build()

    edge_pairs = {(edge.source, edge.target) for edge in graph.edges()}
    assert ("a", "b") in edge_pairs
    assert ("a", "c") in edge_pairs
    assert ("a", "normalize") in edge_pairs
    assert ("normalize", "normalize") not in edge_pairs
    assert graph.predecessors("b") == ("a", "normalize")
    assert graph.successors("a") == ("b", "c", "normalize")


def test_incompatible_types_do_not_connect() -> None:
    registry = ToolRegistry()
    registry.register(a)

    @tool(consumes=[Y], produces=[str])
    async def needs_y(value: Y) -> str:
        return str(value.value)

    registry.register(needs_y)
    graph = DependencyGraphBuilder(registry).build()
    assert graph.edges() == ()
