import pytest

from capability_runtime import (
    CapabilityRegistry,
    InvalidCapabilityError,
    ToolRegistry,
    tool,
)


@tool(
    layer="read",
    capabilities={"order.read", "order.search", "order.history.read"},
)
async def order_db():
    return None


@tool(layer="read", capabilities={"order.read"})
async def order_cache():
    return None


def test_tool_can_declare_multiple_capabilities() -> None:
    assert order_db.spec.capabilities == frozenset(
        {"order.read", "order.search", "order.history.read"}
    )


def test_registry_supports_many_to_many_capability_index() -> None:
    tools = ToolRegistry()
    tools.register(order_db)
    tools.register(order_cache)
    capabilities = CapabilityRegistry.from_tools(tools)

    assert capabilities.providers("order.read") == ("order_cache", "order_db")
    assert capabilities.providers("invoice.send") == ()
    assert capabilities.capabilities_of("order_db") == frozenset(
        {"order.read", "order.search", "order.history.read"}
    )
    assert capabilities.capabilities_of("missing") == frozenset()
    assert capabilities.all() == (
        "order.history.read",
        "order.read",
        "order.search",
    )


@pytest.mark.parametrize(
    "invalid",
    ["RefundCheck", "CHECK_REFUND", "refund check", "refund", ".refund.check"],
)
def test_capability_names_are_strict(invalid: str) -> None:
    with pytest.raises(InvalidCapabilityError):
        CapabilityRegistry().register(invalid, "tool")
