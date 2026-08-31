# Tool Capability Compiler

A typed dependency graph runtime for composable tools.

当前 MVP 验证一个核心假设：Tool 只声明精确类型的 `consumes / produces` 后，系统可以自动建图，从目标 Artifact 反向编译出最小 DAG，并执行该 DAG。它不依赖 LLM、MCP、Web 框架或人工编排的 Pipeline。

## Quick start

```python
import asyncio
from dataclasses import dataclass

from capability_runtime import (
    DependencyGraphBuilder, Goal, Planner, Runtime, ToolRegistry, tool,
)

@dataclass(frozen=True)
class Number:
    value: int

@dataclass(frozen=True)
class Doubled:
    value: int

@tool(consumes=[Number], produces=[Doubled])
async def double(number: Number) -> Doubled:
    return Doubled(number.value * 2)

registry = ToolRegistry()
registry.register(double)

graph = DependencyGraphBuilder(registry).build()
plan = Planner(graph).plan(Goal.of(Doubled), available_inputs={Number})

print(plan.explain())
result = asyncio.run(Runtime(registry).execute(plan, {Number: Number(21)}))
assert result == Doubled(42)
```

## MVP capabilities

- 精确 Python 类型作为 Artifact identity
- async Python Tool decorator 与单输出 contract
- Producer 索引及自动依赖边
- Goal-driven backward planning 与无关 Tool 剪枝
- 多 Provider 按 `priority DESC, name ASC` 确定性选择
- 不可达高优先级 Provider 自动回退
- Cycle detection、Artifact conflict 和领域异常
- 确定性拓扑排序、Artifact 传播与输出校验
- `plan.explain()` 及 Graph inspect API

## Develop

```bash
python -m pytest -q
python -m pip install -e .
python main.py
```

架构约束见 [Phase 0](docs/acceptance/phase0.md)，MVP 验收规格见 [Phase 1](docs/acceptance/phase1.md)。
