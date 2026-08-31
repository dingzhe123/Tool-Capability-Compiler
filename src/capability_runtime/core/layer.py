from __future__ import annotations

from dataclasses import dataclass

from .errors import RegistrationError


@dataclass(frozen=True, slots=True, order=True)
class Layer:
    order: int
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise RegistrationError("Layer name cannot be empty")
        if self.order < 0:
            raise RegistrationError("Layer order cannot be negative")
