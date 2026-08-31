from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class ArtifactKey:
    """The exact Python type used as an artifact's identity."""

    type_: type

    def __post_init__(self) -> None:
        if not isinstance(self.type_, type):
            raise TypeError("ArtifactKey requires a Python type")

    @classmethod
    def of(cls, artifact: ArtifactLike) -> ArtifactKey:
        return artifact if isinstance(artifact, cls) else cls(artifact)

    @property
    def name(self) -> str:
        return self.type_.__name__

    def __str__(self) -> str:
        return self.name


ArtifactLike: TypeAlias = type | ArtifactKey


def artifact_key(value: ArtifactLike) -> ArtifactKey:
    return ArtifactKey.of(value)
