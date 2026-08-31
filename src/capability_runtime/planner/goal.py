from __future__ import annotations

from dataclasses import dataclass

from ..core.artifact import ArtifactKey, ArtifactLike, artifact_key


@dataclass(frozen=True, slots=True)
class Goal:
    produces: ArtifactKey

    def __post_init__(self) -> None:
        object.__setattr__(self, "produces", artifact_key(self.produces))

    @classmethod
    def of(cls, artifact: ArtifactLike) -> Goal:
        return cls(artifact_key(artifact))
