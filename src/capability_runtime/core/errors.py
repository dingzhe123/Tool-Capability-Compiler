from __future__ import annotations

from collections.abc import Iterable

from .artifact import ArtifactKey


class GraphRuntimeError(Exception):
    """Base class for public domain errors."""


class ToolRegistrationError(GraphRuntimeError):
    pass


class DuplicateToolError(ToolRegistrationError):
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool already registered: {tool_name}")


class ToolNotFoundError(GraphRuntimeError):
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool not found: {tool_name}")


class MissingProducerError(GraphRuntimeError):
    def __init__(self, artifact: ArtifactKey) -> None:
        self.artifact = artifact
        super().__init__(f"No producer found for artifact: {artifact}")


class UnsatisfiedDependencyError(GraphRuntimeError):
    def __init__(self, artifact: ArtifactKey, reasons: Iterable[BaseException] = ()) -> None:
        self.artifact = artifact
        self.reasons = tuple(reasons)
        detail = "; ".join(str(reason) for reason in self.reasons)
        suffix = f" ({detail})" if detail else ""
        super().__init__(f"No satisfiable provider for artifact: {artifact}{suffix}")


class CyclicDependencyError(GraphRuntimeError):
    def __init__(self, chain: Iterable[ArtifactKey]) -> None:
        self.chain = tuple(chain)
        rendered = " -> ".join(str(artifact) for artifact in self.chain)
        super().__init__(f"Cyclic dependency detected: {rendered}")


class InvalidExecutionPlanError(GraphRuntimeError):
    pass


class ArtifactConflictError(InvalidExecutionPlanError):
    def __init__(self, artifact: ArtifactKey, producers: Iterable[str]) -> None:
        self.artifact = artifact
        self.producers = tuple(producers)
        names = ", ".join(self.producers)
        super().__init__(f"Artifact {artifact} has multiple selected producers: {names}")


class MissingRuntimeInputError(GraphRuntimeError):
    def __init__(self, tool_name: str, artifact: ArtifactKey) -> None:
        self.tool_name = tool_name
        self.artifact = artifact
        super().__init__(f"Tool {tool_name} is missing runtime input: {artifact}")


class ArtifactNotFoundError(GraphRuntimeError):
    def __init__(self, artifact: ArtifactKey) -> None:
        self.artifact = artifact
        super().__init__(f"Artifact not found in execution state: {artifact}")


class InvalidToolOutputError(GraphRuntimeError):
    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Invalid output from tool {tool_name}: {message}")


class ToolExecutionError(GraphRuntimeError):
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool execution failed: {tool_name}")
