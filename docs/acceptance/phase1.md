# Phase 1 — Layered Tool Topology MVP

## 1. 唯一目标

> **证明可以通过 `layer / provider / worker` 声明，生成一个可约束、可检查、可供 Agent 搜索的分层 Tool Topology。**

Phase 1 只构造 Declared Topology，不选择最佳路线、不调用 Tool、不从业务结果学习。

## 2. 必须实现

```text
Layer
LayerRegistry
ToolSpec
ToolNode
ToolRegistry
ToolEdge
Topology
TopologyBuilder
TopologyValidationWarning
RoutePlan
```

## 3. Tool 声明

```python
@tool(
    layer="read",
    providers="all",
    workers=["policy_check", "summarizer"],
    consumes=[Query],
    produces=[Order],
    description="Read an order from the database",
)
async def get_order(query: Query) -> Order:
    ...
```

规则：

- Tool 名称唯一，默认使用函数名；
- Tool 必须属于已注册 Layer；
- Provider 和 Worker 默认 `all`；
- 显式白名单必须引用存在且位于正确相邻层的 Tool；
- 实现保持 async，但本阶段不执行；
- Schema 参数数量与函数位置参数数量一致。

## 4. Layer 规则

- Layer 名称和顺序均唯一；
- 顺序必须连续；
- 只在 `N → N+1` 之间建立候选边；
- 禁止同层边、反向边和跨层边。

## 5. Edge 规则

```text
A → B exists
IFF
layer(B).order = layer(A).order + 1
AND A.workers allows B
AND B.providers allows A
```

默认 `all / all` 时，相邻两层全连接。任何一侧显式排除，边都不存在。

## 6. Schema Validation

Schema 不参与建边。对于已经由业务声明允许的边：

- 两边均声明 Schema 且无精确类型重叠时，产生 `SCHEMA_MISMATCH`；
- 告警不得删除 Edge；
- 任一侧未声明 Schema 时，不做推断。

## 7. Topology Inspect

至少支持：

```python
topology.layers()
topology.nodes()
topology.nodes_in_layer(name)
topology.edges()
topology.warnings()
topology.predecessors(tool)
topology.successors(tool)
topology.has_edge(source, target)
```

相同 Registry 必须产生相同顺序的 Node、Edge 和 Warning。

## 8. RoutePlan

RoutePlan 以分层集合表达候选执行子图：

```python
RoutePlan.from_groups(
    topology,
    [
        {"db", "rag"},
        {"policy_check"},
        {"refund"},
    ],
)
```

校验规则：

- 每组至少一个 Tool；
- 同组 Tool 必须属于同一 Layer；
- 相邻 Route 组必须属于相邻 Layer；
- 每个非末层节点至少连接一个下一组节点；
- 每个非首层节点至少连接一个上一组节点。

本阶段 RoutePlan 由调用方提供，不实现 Agent Planner。

## 9. 验收场景

### 默认密集拓扑

```text
Read:    DB, RAG
Analyze: Policy, Risk
```

默认得到四条边。

### 双向白名单交集

```text
DB.workers = [Policy]
Policy.providers = [DB, RAG]
```

得到 `DB → Policy`，不得得到 `DB → Risk`。

### 跨层引用

Read Tool 直接把 Act Tool 声明为 Worker 时，构建失败并给出领域错误。

### Schema 告警

显式允许 `Order Producer → RefundRequest Consumer` 时，边保留并产生告警。

### 多节点 Route

必须支持：

```text
{DB, RAG} → {PolicyCheck} → {Refund}
```

### 断开 Route

Route 中包含没有入边或出边的选中节点时必须拒绝。

## 10. 非目标

```text
Goal Artifact
Backward Planner
Minimal DAG
Provider Priority
Runtime Execution
Execution State
Fast / Slow Regression
Trace
Evaluation
Pruning
Ranking
```

## 11. Definition of Done

- [ ] Layer 和 Tool 可注册且命名唯一
- [ ] 默认相邻层全连接
- [ ] Provider / Worker 双向白名单正确取交集
- [ ] 非相邻引用被拒绝
- [ ] Schema 不决定 Edge
- [ ] Schema 明显不匹配产生非阻断告警
- [ ] Topology 可确定性检查
- [ ] RoutePlan 支持同层多个 Tool
- [ ] RoutePlan 拒绝未连接子图
- [ ] 无 Artifact-driven Planner
- [ ] 无 Tool Runtime
- [ ] 单元和退款拓扑集成测试通过
