from __future__ import annotations

import re

from .errors import InvalidCapabilityError

_CAPABILITY_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$"
)


def validate_capability_name(value: str) -> str:
    """Validate and return a canonical lower-case, dot-separated capability."""

    if not isinstance(value, str) or not _CAPABILITY_PATTERN.fullmatch(value):
        raise InvalidCapabilityError(
            "Capability must be lowercase dot-separated segments, "
            f"for example 'order.read': {value!r}"
        )
    return value
