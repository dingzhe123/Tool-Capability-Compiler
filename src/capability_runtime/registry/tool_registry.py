from __future__ import annotations

import logging

from ..core.artifact import ArtifactKey, ArtifactLike, artifact_key
from ..core.errors import DuplicateToolError, ToolNotFoundError, ToolRegistrationError
from ..core.tool import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools_by_name: dict[str, Tool] = {}
        self._producers_by_artifact: dict[ArtifactKey, list[Tool]] = {}

    def register(self, registered_tool: Tool) -> None:
        if not isinstance(registered_tool, Tool):
            raise ToolRegistrationError("Registered value does not implement Tool")
        name = registered_tool.spec.name
        if name in self._tools_by_name:
            raise DuplicateToolError(name)
        self._tools_by_name[name] = registered_tool
        for produced in registered_tool.spec.produces:
            self._producers_by_artifact.setdefault(produced, []).append(registered_tool)
        logger.debug("tool registered: %s", name)

    def get(self, name: str) -> Tool:
        try:
            return self._tools_by_name[name]
        except KeyError as exc:
            raise ToolNotFoundError(name) from exc

    def all(self) -> list[Tool]:
        return [self._tools_by_name[name] for name in sorted(self._tools_by_name)]

    def producers_of(self, artifact: ArtifactLike) -> list[Tool]:
        key = artifact_key(artifact)
        return sorted(
            self._producers_by_artifact.get(key, ()),
            key=lambda candidate: (-candidate.spec.priority, candidate.spec.name),
        )
