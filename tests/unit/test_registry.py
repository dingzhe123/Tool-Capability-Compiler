from dataclasses import dataclass

import pytest

from capability_runtime import (
    ArtifactKey,
    DuplicateToolError,
    ToolNotFoundError,
    ToolRegistry,
    tool,
)


@dataclass(frozen=True)
class Value:
    value: str


@tool(produces=[Value], priority=1)
async def make_value() -> Value:
    return Value("a")


@tool(name="other_value", produces=[Value], priority=10)
async def make_other_value() -> Value:
    return Value("b")


def test_register_get_and_find_producers() -> None:
    registry = ToolRegistry()
    registry.register(make_value)
    registry.register(make_other_value)

    assert registry.get("make_value") is make_value
    assert [item.spec.name for item in registry.all()] == ["make_value", "other_value"]
    assert [item.spec.name for item in registry.producers_of(Value)] == [
        "other_value",
        "make_value",
    ]
    assert registry.producers_of(ArtifactKey.of(str)) == []


def test_duplicate_and_missing_tools_use_domain_errors() -> None:
    registry = ToolRegistry()
    registry.register(make_value)

    with pytest.raises(DuplicateToolError):
        registry.register(make_value)
    with pytest.raises(ToolNotFoundError):
        registry.get("missing")
