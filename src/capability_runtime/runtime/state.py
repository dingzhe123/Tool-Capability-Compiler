from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..core.artifact import ArtifactKey, ArtifactLike, artifact_key
from ..core.errors import ArtifactNotFoundError


class ExecutionState:
    def __init__(self, initial: Mapping[ArtifactLike, Any] | None = None) -> None:
        self._values: dict[ArtifactKey, Any] = {
            artifact_key(key): value for key, value in (initial or {}).items()
        }

    def put(self, artifact: ArtifactLike, value: Any) -> None:
        self._values[artifact_key(artifact)] = value

    def get(self, artifact: ArtifactLike) -> Any:
        key = artifact_key(artifact)
        try:
            return self._values[key]
        except KeyError as exc:
            raise ArtifactNotFoundError(key) from exc

    def contains(self, artifact: ArtifactLike) -> bool:
        return artifact_key(artifact) in self._values

    def update(self, values: Mapping[ArtifactLike, Any]) -> None:
        for artifact, value in values.items():
            self.put(artifact, value)
