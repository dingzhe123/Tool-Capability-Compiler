from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .artifact import ArtifactKey


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    consumes: tuple[ArtifactKey, ...]
    produces: tuple[ArtifactKey, ...]
    priority: int = 0


@runtime_checkable
class Tool(Protocol):
    @property
    def spec(self) -> ToolSpec: ...

    async def execute(
        self, inputs: dict[ArtifactKey, Any]
    ) -> dict[ArtifactKey, Any]: ...
