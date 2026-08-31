# Phase 0 — 项目开发总纲领

## 0. 文档定位

本文档定义项目的核心目标、架构边界、核心抽象、设计原则、阶段划分与验收标准。

后续所有 Spec、Issue、PR、架构调整和功能实现，应优先满足本文档中的约束。

如果某项实现与本文档冲突，应优先修改实现；如果确认原设计原则不再适用，则必须先修改本文档，再推进代码变更。

---

# 1. 项目暂定定位

项目暂定定义为：

> **基于类型化能力图的智能体工具编排与执行运行时。**

英文定位：

> **A typed capability graph runtime for composable AI agents.**

项目解决的核心问题不是：

> 如何让 LLM 调用 Tool。

而是：

> 当系统中存在大量 Tool、MCP Tool、API、Workflow 或其他 Agent 时，如何自动理解这些能力之间的依赖关系，并根据用户目标动态生成最小、安全、可执行的工具调用子图。

项目最终期望形成：

```text
Tool / MCP / API
        ↓
Capability Definition
        ↓
Capability Graph
        ↓
Goal Resolution
        ↓
Subgraph Planning
        ↓
Policy Validation
        ↓
Execution Plan
        ↓
Runtime Execution
```

---

# 2. 项目核心问题

传统 Agent 工具调用通常采用：

```text
LLM
 ↓
Tool List
 ↓
Tool Selection
 ↓
Tool Execution
```

随着工具数量增加，会出现以下问题：

### 2.1 Tool 数量膨胀

Agent 可能同时暴露几十甚至上百个工具。

导致：

* Tool selection 准确率下降；
* Prompt Token 增长；
* 相似工具难以区分；
* LLM 更容易选择错误工具；
* 工具组合关系难以维护。

---

### 2.2 Pipeline 依赖人工定义

传统 Workflow 通常需要人工：

```python
graph.add_edge("get_order", "check_refund")
graph.add_edge("check_refund", "refund")
```

随着业务增加：

```text
新增 Tool
→ 修改 Pipeline
→ 修改 Graph
→ 修改 Agent
→ 重新测试
```

工具与业务 Pipeline 高度耦合。

---

### 2.3 Tool 缺少语义信息

传统 Tool Schema 通常只有：

```text
name
description
parameters
```

但真正进行 Agent 编排还需要：

```text
这个 Tool 需要什么？
它能够产生什么？
它属于什么能力？
是否产生副作用？
风险等级是多少？
需要什么权限？
```

因此项目需要把 Tool 从：

```text
Callable Function
```

提升为：

```text
Capability Node
```

---

### 2.4 LLM 承担过多规划责任

传统 Agent 中 LLM 同时负责：

```text
理解目标
选择工具
决定顺序
理解依赖
检查结果
决定下一步
```

其中大量工作其实是确定性的工程问题。

例如：

```text
refund_order
requires RefundDecision

RefundDecision
requires Order + RefundPolicy
```

这种依赖关系不应该每次让 LLM 重新推理。

---

# 3. 核心设计理念

项目的核心设计原则为：

> **让 LLM 负责语义不确定性，让 Runtime 负责结构确定性。**

LLM 主要负责：

```text
Goal Understanding
Semantic Matching
Ambiguous Decision
```

Runtime 主要负责：

```text
Dependency Resolution
Type Validation
Graph Search
Policy Validation
Execution Ordering
State Propagation
```

因此系统不是一个纯 LLM Planner。

它更接近：

```text
Compiler
+
Dependency Resolver
+
Workflow Runtime
+
Policy Engine
```

---

# 4. 核心抽象

整个系统围绕以下五个核心对象设计：

```text
Tool
Capability
Artifact
Graph
Goal
```

---

# 5. Tool

Tool 是系统最底层的执行单元。

Tool 可以来自：

```text
Python Function
HTTP API
MCP Tool
RPC
Workflow
其他 Agent
```

Runtime 不应关心 Tool 底层实现方式。

所有 Tool 必须统一转换为：

```text
ToolSpec
```

---

## 5.1 ToolSpec

概念模型：

```python
ToolSpec(
    name="refund_order",

    capability="order.refund",

    consumes={
        "Order",
        "RefundDecision",
    },

    produces={
        "RefundResult",
    },

    layer="act",

    effects={
        "external_write",
        "money_transfer",
    },

    risk="high",

    permissions={
        "refund.execute",
    },
)
```

Phase 0 规定 ToolSpec 至少需要表达以下概念：

```text
name
capability
consumes
produces
layer
effects
risk
permissions
```

具体 Python Schema 在后续 Phase 中确定。

---

# 6. Artifact

Tool 之间不直接通过函数名建立依赖。

依赖关系主要通过：

```text
Artifact
```

表达。

Artifact 表示系统中的结构化数据或事实。

例如：

```text
Order
User
RefundPolicy
RefundDecision
RefundResult
EmailContent
```

例如：

```text
get_order

produces:
    Order
```

而：

```text
check_refund

consumes:
    Order
    RefundPolicy

produces:
    RefundDecision
```

因此系统可以自动推导：

```text
get_order
     ↓
check_refund
```

---

# 7. Capability

Capability 表示：

> Tool 能够向系统提供的业务能力。

例如：

```text
order.read
order.refund
refund.check
policy.read
email.send
user.read
```

Capability 与 Tool 必须解耦。

例如：

```text
Capability:
    order.read
```

可能存在多个 Provider：

```text
mysql_order_reader
erp_order_reader
mock_order_reader
```

因此：

```text
Agent
  ↓
Capability
  ↓
Provider
```

而不是：

```text
Agent
  ↓
Concrete Tool
```

这是项目的重要架构原则。

---

# 8. Layer

Tool 可以按照逻辑职责划分 Layer。

Phase 0 暂定四层：

```text
Observe
Transform
Decide
Act
```

---

## 8.1 Observe

负责获取事实。

例如：

```text
SQL Query
RAG
Web Search
API Query
User Profile Query
Order Query
```

特点：

```text
通常无外部副作用
主要产生 Artifact
```

---

## 8.2 Transform

负责数据处理。

例如：

```text
Extract
Aggregate
Rank
Calculate
Parse
Normalize
Generate
```

特点：

```text
Pure Computation
尽量无外部状态变化
```

---

## 8.3 Decide

负责业务判断。

例如：

```text
Refund Eligibility
Risk Check
Permission Decision
Policy Matching
Strategy Selection
```

输出通常是：

```text
Decision Artifact
```

---

## 8.4 Act

负责产生外部副作用。

例如：

```text
Refund
Send Email
Update Order
Create Record
Delete Resource
Send Message
```

Act 层必须受到更加严格的：

```text
Policy
Permission
Risk
```

控制。

---

# 9. Layer 不是硬编码 Pipeline

必须明确：

```text
Observe
→ Transform
→ Decide
→ Act
```

只是逻辑分层。

不是要求每一个 Pipeline 都必须经过四层。

合法路径可能包括：

```text
Observe → Act
```

或者：

```text
Observe → Transform → Act
```

甚至：

```text
Transform → Transform
```

Layer 的主要作用是：

```text
约束非法边
辅助策略控制
辅助风险判断
辅助可视化
```

而不是规定固定执行流程。

---

# 10. Graph

系统内部维护：

> **Capability Graph**

Node 主要表示：

```text
Tool / Capability Provider
```

Edge 表示：

```text
Tool A 的输出
可以作为
Tool B 的输入
```

但 Schema Compatible 只是建立 Edge 的必要条件之一。

---

# 11. Edge 生成规则

禁止采用：

> 新增 Tool 后默认与下一层所有 Tool 全连接。

否则会导致：

```text
Graph Explosion
```

同时产生严重安全问题。

Phase 0 规定：

```text
Edge(A, B)
```

至少必须满足：

```text
Type Compatible
AND
Capability Compatible
AND
Layer Compatible
AND
Policy Allowed
```

概念表示为：

```text
Possible Edge
=
Schema Match
∩ Capability Match
∩ Layer Constraint
∩ Policy Constraint
```

---

# 12. 自动建图

Tool 注册以后，Graph Builder 应能够自动分析：

```text
consumes
produces
capability
layer
```

并构建候选依赖图。

例如：

```text
get_order
produces:
    Order
```

```text
check_refund
consumes:
    Order
produces:
    RefundDecision
```

```text
refund_order
consumes:
    RefundDecision
```

自动形成：

```text
get_order
     ↓
check_refund
     ↓
refund_order
```

这是项目核心能力之一。

---

# 13. Goal

用户请求不应该直接映射成 Tool。

应该首先转化为：

```text
Goal
```

例如：

```text
用户：
退款订单 123
```

转化为：

```text
Goal:
    capability = "order.refund"
```

Goal 是：

```text
用户语义
```

和：

```text
Capability Graph
```

之间的边界。

---

# 14. Backward Planning

Pipeline 不应该默认从所有入口向前探索。

核心规划策略采用：

> **Goal-driven backward planning**

首先找到满足 Goal 的目标 Capability。

例如：

```text
Goal:
order.refund
```

找到：

```text
refund_order
```

它需要：

```text
RefundDecision
```

再向前寻找：

```text
谁能产生 RefundDecision？
```

得到：

```text
check_refund
```

继续：

```text
check_refund
requires:
    Order
    RefundPolicy
```

继续反向解析：

```text
get_order
get_refund_policy
```

最终得到最小子图：

```text
get_order ───────────┐
                     ↓
               check_refund
                     ↑
get_refund_policy ───┘
                     ↓
                refund_order
```

---

# 15. Graph Pruning

系统的主要目标不是生成完整 Capability Graph。

完整 Graph 只是基础设施。

真正执行前必须生成：

```text
Executable Subgraph
```

目标是：

```text
100 Tools
↓
Goal Planning
↓
5 Candidate Tools
↓
Execution DAG
```

而不是：

```text
100 Tools
↓
全部暴露给 LLM
```

---

# 16. Tool 注册原则

项目必须支持：

```text
Plug-and-Play Tool Registration
```

新增 Tool 后：

```text
Register Tool
      ↓
Parse Metadata
      ↓
Update Capability Registry
      ↓
Update Dependency Graph
      ↓
Automatically Unlock New Paths
```

原则上：

> 新增业务 Tool 不应该要求修改核心 Runtime。

这是项目区别于传统人工 Pipeline 的关键价值之一。

---

# 17. 自动组合不等于自动授权

必须明确：

> 能组成 Pipeline，不意味着允许执行 Pipeline。

例如：

```text
get_user
   ↓
delete_account
```

即使 Schema 完全兼容，也必须经过 Policy Engine。

因此：

```text
Reachable
≠
Executable
```

系统至少存在三个概念：

```text
Possible Graph
Allowed Graph
Executable Graph
```

---

# 18. Effect

Tool 必须能够声明副作用。

Phase 0 暂定 Effect 类型包括：

```text
none
internal_read
external_read
internal_write
external_write
message_send
resource_create
resource_delete
money_transfer
```

具体枚举后续允许调整。

Effect 主要用于：

```text
Policy
Audit
Risk
Execution Guard
```

---

# 19. Risk

Tool 应允许声明风险等级。

初始可以简单采用：

```text
low
medium
high
critical
```

例如：

```text
get_order
risk=low
```

```text
send_email
risk=medium
```

```text
delete_account
risk=high
```

```text
transfer_money
risk=critical
```

Risk 本身不直接决定是否执行。

它作为 Policy Engine 的输入。

---

# 20. Permission

Capability 和 Tool 均允许定义 Permission。

例如：

```text
order.read
refund.check
refund.execute
user.delete
email.send
```

Planning 阶段应该尽可能提前裁剪当前 Agent 无权调用的 Node。

而不是等到执行阶段才失败。

---

# 21. Policy Engine

Policy Engine 负责判断：

```text
Graph Edge 是否允许
Tool 是否允许
数据是否允许流向目标 Tool
当前 Agent 是否有权限
高风险操作是否需要额外条件
```

Phase 0 不要求实现复杂 Policy DSL。

第一阶段可以只实现：

```text
allow / deny
```

但架构必须预留 Policy 层。

---

# 22. Planner

Planner 负责：

```text
Goal
↓
Capability Resolution
↓
Backward Search
↓
Candidate Subgraph
↓
Constraint Filtering
↓
Execution DAG
```

Phase 0 明确：

Planner 初期优先采用：

```text
Deterministic Graph Algorithm
```

而不是：

```text
LLM Generated Workflow
```

LLM 仅用于：

```text
Goal → Capability
```

或者无法确定的语义选择。

---

# 23. 多 Provider 问题

一个 Artifact 或 Capability 可能存在多个 Provider。

例如：

```text
Order

← MySQL
← ERP
← Cache
← Mock
```

因此 Planner 后续需要支持：

```text
Provider Selection
```

未来可以根据：

```text
cost
latency
reliability
freshness
permission
risk
priority
```

进行评分。

但 Phase 1 不需要立即实现复杂优化器。

初始允许：

```text
priority
```

决定 Provider。

---

# 24. Runtime

Runtime 负责执行 Planner 产生的 DAG。

Runtime 不负责：

```text
理解用户意图
重新设计 Pipeline
```

Runtime 主要负责：

```text
Node Execution
State Management
Artifact Propagation
Dependency Resolution
Error Handling
Retry
Timeout
Audit
```

---

# 25. State

执行过程中的数据统一进入：

```text
Execution State
```

例如：

```text
{
    "Order": ...,
    "RefundPolicy": ...,
    "RefundDecision": ...,
}
```

Node 从 State 获取自己声明的 Artifact。

Node 输出继续写入 State。

避免 Node 之间产生大量隐式 Python 调用关系。

---

# 26. DAG 优先

Phase 0 / Phase 1 执行模型优先限制为：

```text
DAG
```

暂不支持：

```text
Loop
Cycle
Recursive Agent
Infinite Planning
```

原因：

```text
降低 Runtime 复杂度
保证可解释性
方便 Debug
方便静态验证
```

循环能力未来可以作为高级功能加入。

---

# 27. 可解释性

系统必须天然支持解释：

```text
为什么调用这个 Tool？
为什么它依赖另一个 Tool？
为什么没有选择另一个 Provider？
为什么某条路径被拒绝？
```

理想输出：

```text
Goal:
order.refund

Selected Tool:
refund_order

Dependency:
refund_order requires RefundDecision

Producer:
check_refund produces RefundDecision

Dependency:
check_refund requires Order

Producer:
get_order produces Order
```

Capability Graph 本身应该成为解释来源。

---

# 28. Observability

系统未来必须能够记录：

```text
Execution ID
Goal
Selected Subgraph
Node Start
Node End
Node Input
Node Output Metadata
Latency
Error
Retry
Policy Decision
```

但默认不得记录：

```text
Secret
Credential
敏感原始数据
```

完整 Observability 在后续阶段实现。

---

# 29. 不做什么

Phase 0 必须明确项目边界。

本项目暂时不做：

### 29.1 不做通用聊天 Agent

项目核心是：

```text
Tool Composition Runtime
```

不是：

```text
Chatbot Framework
```

---

### 29.2 不做 LangGraph 替代品

不以：

```text
人工编排任意复杂 Workflow
```

作为核心竞争点。

重点是：

```text
自动 Capability Discovery
+
自动 Dependency Graph
+
Goal-driven Planning
```

---

### 29.3 不做完整 BPM / Workflow Engine

暂不追求：

```text
Human Task
BPMN
长事务
复杂 Compensation
人工审批流设计器
```

---

### 29.4 不做 Multi-Agent Framework

Phase 1 不实现：

```text
Agent → Agent
```

后续可以把另一个 Agent 看作 Tool Provider。

---

### 29.5 不优先做 UI

Phase 1 以：

```text
Python SDK
CLI
Graph Debug Output
```

为主。

Graph Web UI 后续再实现。

---

# 30. Phase 1 最小验证目标

Phase 1 只验证一个核心命题：

> **仅通过 Tool Metadata，系统是否可以自动构建依赖图，并根据 Goal 自动生成一个正确的最小执行 DAG。**

只需要约 6～10 个工具。

推荐 Demo：

```text
get_user
get_order
get_refund_policy
check_refund
refund_order
send_email
```

目标：

```text
Goal:
refund an order
```

自动生成：

```text
get_order ───────────┐
                     ↓
               check_refund
                     ↑
get_refund_policy ───┘
                     ↓
                refund_order
```

---

# 31. Phase 1 必须实现

最小核心模块：

```text
ToolSpec
Artifact Definition
Tool Registry
Capability Registry
Graph Builder
Dependency Resolver
Backward Planner
Execution DAG
Basic Runtime
```

---

# 32. Phase 1 暂不实现

以下能力全部延后：

```text
复杂 LLM Planner
复杂 Policy DSL
复杂权限系统
MCP 自动扫描
OpenAPI 自动转换
成本优化器
并行调度优化
分布式执行
持久化 Runtime
Human-in-the-loop
Graph UI
Multi-Agent
Loop
```

必须避免 Phase 1 过度设计。

---

# 33. Phase 1 Demo 验收

必须能够：

### Case 1

注册：

```text
A produces X
B consumes X
```

自动生成：

```text
A → B
```

---

### Case 2

注册：

```text
A produces X
B consumes X produces Y
C consumes Y
```

系统自动生成：

```text
A → B → C
```

---

### Case 3

系统中存在：

```text
20 Tools
```

Goal 只需要：

```text
A → B → C
```

Planner 返回：

```text
3 Nodes
```

而不是全部 Tool。

---

### Case 4

存在不兼容类型：

```text
A produces Order
B consumes User
```

不得产生 Edge。

---

### Case 5

存在两种 Provider：

```text
mysql_get_order
mock_get_order
```

系统能够根据简单 Priority 选择其中一个。

---

### Case 6

DAG 执行结束后：

```text
Artifact
```

能够正确从上游传播给下游。

---

# 34. Phase 2

Phase 2 目标：

> 从纯 Dependency Graph 升级为 Capability Graph。

增加：

```text
Capability
Layer
Effect
Risk
Permission
Basic Policy
```

Graph Edge 开始从：

```text
Schema Compatible
```

升级为：

```text
Schema
+
Capability
+
Layer
+
Policy
```

---

# 35. Phase 3

Phase 3：

> Tool Ecosystem Integration。

支持：

```text
Python Tool
MCP Tool
OpenAPI
HTTP Tool
```

统一转换成：

```text
ToolSpec
```

核心目标：

```text
Backend Agnostic
```

---

# 36. Phase 4

Phase 4：

> Intelligent Planning。

加入：

```text
Goal Parser
Semantic Capability Matching
Multiple Candidate Plans
Provider Scoring
Cost Model
Latency Model
Reliability Model
```

形成：

```text
Candidate DAG
    ↓
Plan Scoring
    ↓
Best Execution DAG
```

---

# 37. Phase 5

Phase 5：

> Production Runtime。

增加：

```text
Timeout
Retry
Circuit Breaker
Caching
Tracing
Metrics
Audit
Checkpoint
Failure Recovery
```

---

# 38. Phase 6

Phase 6：

> Advanced Capability Graph。

可探索：

```text
Dynamic Capability Discovery
Agent as Tool
Cross-Agent Composition
Conditional Graph
Loop
Human Approval
Long-running Workflow
Distributed Runtime
Capability Marketplace
```

---

# 39. 推荐代码模块边界

长期目标目录可以演进为：

```text
src/
├── core/
│   ├── tool.py
│   ├── artifact.py
│   ├── capability.py
│   └── types.py
│
├── registry/
│   ├── tool_registry.py
│   └── capability_registry.py
│
├── graph/
│   ├── builder.py
│   ├── dependency.py
│   └── validation.py
│
├── planner/
│   ├── goal.py
│   ├── backward.py
│   ├── pruning.py
│   └── scoring.py
│
├── policy/
│   ├── engine.py
│   ├── risk.py
│   └── permission.py
│
├── runtime/
│   ├── executor.py
│   ├── state.py
│   └── context.py
│
├── adapters/
│   ├── python.py
│   ├── mcp.py
│   └── openapi.py
│
└── observability/
    ├── trace.py
    └── events.py
```

Phase 1 不要求一次创建所有模块。

目录结构应随实际实现演进。

---

# 40. 核心架构规则

后续开发必须优先遵守以下规则。

## Rule 1

Tool 不直接依赖具体 Tool。

优先依赖：

```text
Artifact
Capability
```

---

## Rule 2

Tool 不应该知道完整 Pipeline。

Tool 只声明：

```text
我需要什么
我产生什么
我提供什么能力
```

---

## Rule 3

Pipeline 应尽可能由 Graph 推导。

禁止大量硬编码：

```python
if goal == "refund":
    call_a()
    call_b()
    call_c()
```

---

## Rule 4

LLM 不承担可以由确定性程序完成的工作。

例如：

```text
dependency resolution
type matching
topological sorting
permission filtering
```

都应由 Runtime 完成。

---

## Rule 5

Graph Planning 和 Graph Execution 必须分离。

即：

```text
Plan
≠
Execute
```

必须允许：

```text
先生成 ExecutionPlan
再验证
再执行
```

---

## Rule 6

Read 与 Write 必须在语义层面区分。

尤其：

```text
Act
```

不得因为 Schema 可连接就自动获得执行权限。

---

## Rule 7

类型兼容不代表业务兼容。

```text
Type Match
```

只能产生 Candidate Edge。

最终 Edge 仍需受到 Capability / Policy 约束。

---

## Rule 8

Reachability 不等于 Authorization。

```text
Graph 上能到达
```

不意味着：

```text
当前 Agent 可以执行
```

---

## Rule 9

核心 Runtime 不绑定 LLM Provider。

不得把：

```text
OpenAI
Anthropic
Qwen
```

写入核心依赖模型。

LLM 应作为可替换 Adapter。

---

## Rule 10

核心 Runtime 不绑定 MCP。

MCP 是：

```text
Tool Provider
```

之一。

不是项目本身的基础抽象。

---

# 41. 判断一个新功能是否应该加入

每次准备新增功能时，需要回答：

```text
它是否强化 Capability Graph？

它是否提高自动组合能力？

它是否减少 LLM 的非必要决策？

它是否提高执行安全性？

它是否提高 Tool 的可复用性？

它是否让新 Tool 更容易 Plug-and-Play？
```

如果全部答案都是：

```text
No
```

则该功能大概率不属于核心范围。

---

# 42. 项目核心竞争点

项目未来不应主要宣传：

```text
支持多少模型
支持多少 Tool
支持多少 Agent
```

真正应该形成的核心能力是：

### 1. Typed Tool Contract

```text
consumes / produces
```

---

### 2. Automatic Dependency Graph

```text
Tool Registry
→ Graph
```

---

### 3. Capability Abstraction

```text
Capability
≠
Provider
```

---

### 4. Goal-driven Graph Compilation

```text
Goal
→ Minimal Subgraph
```

---

### 5. Policy-aware Planning

```text
Reachable
→ Allowed
→ Executable
```

---

### 6. Dynamic Composition

```text
Register New Tool
→ Unlock New Capability Paths
```

这是项目最关键的长期方向。

---

# 43. 项目的核心公式

可以用三个公式概括整个项目。

### Tool

```text
Tool
=
Capability
+
Contract
+
Effect
+
Policy Metadata
```

### Edge

```text
Edge
=
Type Compatibility
∩
Capability Compatibility
∩
Layer Constraint
∩
Policy
```

### Pipeline

```text
Executable Pipeline
=
Goal
→ Capability Graph
→ Backward Search
→ Pruning
→ Policy Validation
→ Execution DAG
```

---

# 44. 最终愿景

系统最终希望做到：

开发者只负责：

```text
定义 Tool
```

例如：

```text
I consume:
    Order

I produce:
    RefundDecision

I provide:
    refund.check
```

系统自动完成：

```text
Register
↓
Understand
↓
Connect
↓
Plan
↓
Validate
↓
Execute
```

最终将 Agent 工具系统从：

```text
人工 Pipeline 编排
```

推进到：

```text
声明式能力定义
+
自动 Capability Graph 编译
```

---

# 45. Phase 0 完成标准

Phase 0 不产生业务功能代码。

Phase 0 完成的标志是团队对以下问题形成统一答案：

```text
项目解决什么问题？
什么是 Tool？
什么是 Artifact？
什么是 Capability？
Graph 的 Node 是什么？
Graph 的 Edge 如何产生？
为什么采用 backward planning？
LLM 在哪里使用？
Runtime 负责什么？
Policy 负责什么？
什么能力暂时不做？
Phase 1 最小验证目标是什么？
```

只有上述问题稳定后，才进入 Phase 1。

---

# 46. Phase 1 唯一核心任务

Phase 1 应始终围绕这一条展开：

> **证明一个 Tool 只声明自己的输入、输出与基础 Metadata 后，系统可以自动构建依赖图，并从一个 Goal 编译出最小可执行 DAG。**

如果 Phase 1 成功验证这一点，则项目核心假设成立。

如果这一点无法成立，则应优先重新评估整个架构，而不是继续增加 MCP、LLM、UI 或 Multi-Agent 等外围能力。
