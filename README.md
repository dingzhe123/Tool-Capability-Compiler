# Tool Capability Compiler

一个面向智能体工具调用的分层路由与拓扑优化框架。

项目不替开发者手工编排一条固定 Workflow，也不根据输入输出类型编译所谓“最小依赖 DAG”。开发者声明一个允许的工具搜索空间，后续由业务场景回归探索路线、评估效果，并让 Active Topology 逐步收敛。

```text
Declare → Initialize → Explore → Evaluate → Prune → Rank → Route
```

当前 Phase 1 只实现 `Declare → Initialize`：

- 有序 Layer 与 Tool Registry
- `provider / worker` 双向白名单
- 相邻层默认全连接
- 确定性的 Declared Topology
- Schema 可执行性告警，不以 Schema 建边
- 支持一层多个节点的 RoutePlan 及拓扑约束校验

## Quick start

```python
from capability_runtime import (
    LayerRegistry, RoutePlan, ToolRegistry, TopologyBuilder, tool,
)

@tool(layer="read", workers=["policy_check"])
async def database(): ...

@tool(
    layer="analyze",
    providers=["database"],
    workers=["refund"],
)
async def policy_check(): ...

@tool(layer="act", providers=["policy_check"])
async def refund(): ...

layers = LayerRegistry()
layers.register("read", 0)
layers.register("analyze", 1)
layers.register("act", 2)

tools = ToolRegistry()
for node in (database, policy_check, refund):
    tools.register(node)

topology = TopologyBuilder(layers, tools).build()
route = RoutePlan.from_groups(
    topology,
    [{"database"}, {"policy_check"}, {"refund"}],
)
print(route.explain())
```

建边公式：

```text
Edge(A, B)
= adjacent(layer(A), layer(B))
  AND A.workers allows B
  AND B.providers allows A
```

`consumes / produces` 仍可声明，但只验证已允许边的 Schema 是否明显不匹配。业务意图决定拓扑，Schema 负责诊断。

## Develop

```bash
python -m pytest -q
python -m pip install -e .
python main.py
```

项目原则见 [Phase 0](docs/acceptance/phase0.md)，当前 MVP 验收规格见 [Phase 1](docs/acceptance/phase1.md)。
