from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .core.artifact import ArtifactKey, ArtifactLike, artifact_key
from .core.errors import ToolRegistrationError
from .core.tool import ToolSpec


@dataclass(frozen=True, slots=True)
class PythonTool:
    spec: ToolSpec
    _function: Callable[..., Awaitable[Any]]

    async def execute(self, inputs: dict[ArtifactKey, Any]) -> dict[ArtifactKey, Any]:
        arguments = [inputs[key] for key in self.spec.consumes]
        result = await self._function(*arguments)
        return {self.spec.produces[0]: result}

    @property
    def __name__(self) -> str:
        return self.spec.name


def tool(
    *,
    consumes: Iterable[ArtifactLike] = (),
    produces: Iterable[ArtifactLike],
    name: str | None = None,
    priority: int = 0,
) -> Callable[[Callable[..., Awaitable[Any]]], PythonTool]:
    """Turn an async Python function into a single-output Tool."""

    consume_keys = tuple(artifact_key(item) for item in consumes)
    produce_keys = tuple(artifact_key(item) for item in produces)

    if len(produce_keys) != 1:
        raise ToolRegistrationError("Phase 1 tools must declare exactly one output")
    if len(set(consume_keys)) != len(consume_keys):
        raise ToolRegistrationError("A tool cannot consume the same artifact twice")

    def decorate(function: Callable[..., Awaitable[Any]]) -> PythonTool:
        if not inspect.iscoroutinefunction(function):
            raise ToolRegistrationError(f"Tool function must be async: {function.__name__}")
        tool_name = name or function.__name__
        if not tool_name or not tool_name.strip():
            raise ToolRegistrationError("Tool name cannot be empty")
        signature = inspect.signature(function)
        positional = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(positional) != len(consume_keys):
            raise ToolRegistrationError(
                f"Tool {tool_name} declares {len(consume_keys)} inputs but has "
                f"{len(positional)} positional parameters"
            )
        return PythonTool(
            spec=ToolSpec(tool_name, consume_keys, produce_keys, priority),
            _function=function,
        )

    return decorate
