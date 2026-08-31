from dataclasses import dataclass

import pytest

from capability_runtime import ArtifactNotFoundError
from capability_runtime.runtime import ExecutionState


@dataclass(frozen=True)
class Value:
    value: int


def test_state_accepts_types_and_artifact_keys() -> None:
    state = ExecutionState({Value: Value(1)})
    assert state.contains(Value)
    assert state.get(Value) == Value(1)

    state.put(Value, Value(2))
    assert state.get(Value) == Value(2)


def test_missing_state_value_is_not_silently_accepted() -> None:
    state = ExecutionState()
    with pytest.raises(ArtifactNotFoundError):
        state.get(Value)
