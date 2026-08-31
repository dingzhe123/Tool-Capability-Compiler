# Phase 0 — Layered Tool Routing 总纲领

## 1. 项目定位

项目定义为：

> **一个面向智能体工具调用的分层路由与拓扑优化框架。**

英文定位：

> **A layered tool-routing and topology optimization framework for AI agents.**

开发者声明“允许的工具搜索空间”，而不是手工编排唯一 Workflow。框架通过业务场景持续探索、评估、统计、剪枝和排名，让可执行拓扑逐渐收敛。

```text
Tool Definition
      ↓
Declared Topology
      ↓
Scenario Battlefield
      ↓
Explore Routes
      ↓
Trace + Evaluation
      ↓
Prune + Rank
      ↓
Active Topology
```

核心判断：

> **Graph 不是答案，Graph 是搜索空间。**

## 2. 废弃的旧主线

以下方向不再是项目主线：

```text
ArtifactKey
Goal(produces=...)
Producer Resolution
Deterministic Backward Planning
Minimal Dependency DAG
Provider Priority
```

输入输出类型不再自动决定业务路径。一个类型可连接，不代表业务上应该连接；一个类型不直接匹配，也不代表 Agent 不能通过语义加工使用该路线。

## 3. 核心对象

```text
Layer
ToolNode
ToolEdge
Topology

Scenario
Battlefield

RoutePlan
Trial
TraceGraph

Evaluation
RouteStats
TopologyVersion
```

Phase 1 只实现第一组，以及最小 RoutePlan 表达。其余对象按后续阶段引入。

## 4. Layer

Layer 表达 Tool 在路由中的逻辑阶段，并具有稳定顺序。例如：

```text
L0 Context
L1 Read
L2 Analyze
L3 Act
```

一次 Route 可以从任意层开始或结束，但只能在相邻层之间传播。每一层可以选择零个、一个或多个 Tool；实际 Route 中出现的层必须非空。

## 5. ToolNode

ToolNode 至少声明：

```text
name
layer
providers
workers
description
consumes
produces
async implementation
```

其中：

- `providers`：允许接收哪些上一层 Tool 的结果；
- `workers`：允许把结果传播给哪些下一层 Tool；
- 默认均为 `all`；
- 显式列表是白名单，空列表代表不允许任何节点。

## 6. ToolEdge

只允许相邻层建边。边规则为：

```text
Edge(A, B)
= layer(B).order = layer(A).order + 1
  AND A.workers allows B
  AND B.providers allows A
```

Provider 和 Worker 是对同一候选边的双向白名单约束，最终取交集。禁止跨层跳跃和仅凭 Schema 自动创造路径。

## 7. Schema 的地位

`consumes / produces` 保留，但语义改为：

```text
Layer + Provider + Worker → 决定 Edge
Schema                    → 验证 Edge
```

显式允许的边如果没有明显 Schema 重叠，应产生 `TopologyValidationWarning`，而不是删除该边或寻找额外中间节点。

## 8. Topology

Topology 表达允许 Agent 搜索的工具组合空间，不表达最终执行答案。

需要区分：

### Declared Topology

由开发者声明生成的最大允许空间。它应保持稳定和可追溯。

### Active Topology

由 Regression、统计和剪枝产生的当前推荐空间。剪枝通过版本或 `enabled=false` 表达，不物理删除 Declared Edge。

Phase 1 只实现 Declared Topology。

## 9. RoutePlan

一次 Route 是一个执行子图，不是严格 Tool Chain。它允许同层多节点：

```python
[
    {"db", "rag"},
    {"policy_check", "risk_check"},
    {"refund"},
]
```

RoutePlan 必须受 Topology 约束，不能包含未声明的边或断开的节点。

## 10. Battlefield

Battlefield 是核心架构，不是普通测试辅助工具。它使用真实业务 Scenario 探索并评价当前 Topology。

### Fast Regression

只使用 Metadata、Topology、Description 和 Schema 判断能力覆盖，不真实执行 Tool。结果至少分为：

```text
COVERED
UNCERTAIN
UNCOVERED
```

它只能证明声明能力看起来可覆盖，不能证明业务真实成功。

### Slow Regression

Agent 在 Topology 约束下实际选择多层节点并执行，产生 Trial、TraceGraph 和 Evaluation。它是拓扑学习的数据来源。

## 11. 评估与剪枝原则

优化对象是 Route / Execution Subgraph，而不只是单 Tool。至少保留以下向量：

```text
success
quality
latency
cost
```

不应过早压成单一分数。不同 Route 可以形成 Fast、Balanced、High Quality 等 Tier。

未被使用的边不能直接删除，因为“无价值”和“尚未探索”不同。剪枝至少需要：

```text
足够 Scenario Coverage
+ 足够 Trial 数量
+ 长期低价值或未使用
+ 剪枝后 Fast Regression 无明显缺口
```

剪枝先标记 Candidate，再验证，最后产生新的 Active Topology Version。

## 12. 阶段路线

| Phase | 目标 | 核心产物 |
| --- | --- | --- |
| 0 | 定义框架原则 | Layer、ToolNode、Topology、Battlefield、Route、Trial |
| 1 | 构建分层拓扑 | Registries、provider/worker、Declared Topology |
| 2 | Fast Regression | Scenario、Metadata Planner、Coverage Report |
| 3 | Slow Regression | Runtime、Agent Routing、Trial、TraceGraph、Evaluation |
| 4 | 拓扑学习与剪枝 | EdgeStats、RouteStats、TopologyVersion |
| 5 | 路径排名 | Success/Quality/Latency/Cost、Pareto Route、Tier |
| 6 | 在线路由 | Active Topology、Route Selection、Load Balancing |

## 13. 当前不做

Phase 1 不实现：

```text
Artifact-driven Planner
Fast / Slow Regression
LLM Planner
Tool Runtime
Trace / Evaluation
统计学习
自动剪枝
Route Ranking
在线负载均衡
MCP / OpenAPI Adapter
UI
```

## 14. 核心公式

```text
Declared Topology
= Layers
  + Tool Nodes
  + Adjacent Dense Connections
  ∩ Provider Allow-list
  ∩ Worker Allow-list
```

```text
Active Topology(t+1)
= Evaluate(Explore(Active Topology(t), Scenarios))
  → Validate
  → Versioned Pruning / Ranking
```

## 15. Phase 0 完成标准

团队需要对以下问题有统一答案：

```text
Graph 为什么是搜索空间？
Layer、provider、worker 分别表达什么？
Edge 如何产生？
Schema 为什么只负责验证？
为什么 Route 不是严格链？
Declared 与 Active Topology 有什么区别？
Fast 与 Slow Regression 分别证明什么？
为什么不能按零使用次数直接剪枝？
各阶段边界是什么？
```
