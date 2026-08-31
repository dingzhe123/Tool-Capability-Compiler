# Phase 1 — Typed Dependency Graph MVP

## 0. 阶段定位

Phase 1 是项目的第一个可运行版本。

本阶段不追求完整的 Capability Graph，也不实现复杂 Agent Runtime。

唯一需要验证的核心假设：

> Tool 只声明自己的输入、输出和基础元数据后，系统可以自动建立工具依赖关系，并根据 Goal 反向解析出一个最小可执行 DAG。

本阶段最终必须能够完成：

```text
Tool Registration
      ↓
Dependency Discovery
      ↓
Dependency Graph
      ↓
Goal
      ↓
Backward Planning
      ↓
Minimal Execution DAG
      ↓
Topological Execution
      ↓
Final Artifact
```

---

# 1. Phase 1 核心目标

Phase 1 必须完成以下能力：

1. 定义统一 ToolSpec
2. 定义 Artifact
3. 注册 Tool
4. 根据 `produces / consumes` 自动构建依赖图
5. 根据 Goal 找到目标 Tool
6. 从目标 Tool 反向解析依赖
7. 生成最小 ExecutionPlan
8. 对 ExecutionPlan 进行拓扑排序
9. 按顺序执行 Tool
10. 在 Tool 之间传递 Artifact
11. 支持简单多 Provider 选择
12. 给出明确的规划与执行错误

---

# 2. Phase 1 非目标

本阶段明确不实现：

```text
Capability Semantic Matching
LLM Goal Parsing
MCP
OpenAPI
HTTP Tool Adapter
Policy Engine
Permission
Risk
Effect
Layer Constraint
复杂 Provider Scoring
Loop
Conditional Branch
Human Approval
Retry
Timeout
Checkpoint
Distributed Runtime
Persistence
Web UI
Multi-Agent
```

Phase 1 不允许因为“未来可能需要”而提前实现这些能力。

---

# 3. MVP 使用方式

最终希望支持类似以下代码：

```python
registry = ToolRegistry()

registry.register(get_order)
registry.register(get_refund_policy)
registry.register(check_refund)
registry.register(refund_order)

graph = DependencyGraphBuilder(registry).build()

planner = Planner(graph)

plan = planner.plan(
    Goal(produces=RefundResult)
)

runtime = Runtime()

result = await runtime.execute(
    plan,
    inputs={
        OrderId: "order_123"
    },
)
```

Planner 最终生成：

```text
get_order ─────────────┐
                       ↓
                 check_refund
                       ↑
get_refund_policy ─────┘
                       ↓
                  refund_order
```

而不是执行 Registry 中所有 Tool。

---

# 4. 核心领域模型

Phase 1 只引入以下核心对象：

```text
ArtifactKey
ToolSpec
Tool
ToolRegistry
DependencyEdge
DependencyGraph
Goal
ExecutionNode
ExecutionPlan
ExecutionState
Planner
Runtime
```

---

# 5. Artifact

Phase 1 中 Artifact 表示 Tool 之间传递的数据。

Artifact 不需要单独注册。

直接使用 Python Type 作为 Artifact Identity。

例如：

```python
@dataclass
class Order:
    id: str
    amount: float
```

```python
@dataclass
class RefundPolicy:
    max_days: int
```

```python
@dataclass
class RefundDecision:
    allowed: bool
    reason: str
```

因此：

```text
Order
RefundPolicy
RefundDecision
```

就是三个 Artifact。

---

# 6. ArtifactKey

内部不要直接把 Python 类型散布在整个系统中。

定义：

```python
@dataclass(frozen=True)
class ArtifactKey:
    type_: type
```

最初可以非常简单。

必须满足：

```python
ArtifactKey(Order) == ArtifactKey(Order)
```

并且可作为：

```python
dict
set
```

的 key。

Phase 1 暂不实现：

```text
Subtype Resolution
Generic Type Resolution
Union
Optional Dependency
Named Artifact
Versioned Artifact
```

只支持：

> exact type match

即：

```text
produces Order
consumes Order
```

才能连接。

---

# 7. ToolSpec

核心数据模型：

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str

    consumes: tuple[ArtifactKey, ...]
    produces: tuple[ArtifactKey, ...]

    priority: int = 0
```

Phase 1 不加入：

```text
capability
layer
effects
risk
permissions
```

这些属于 Phase 2。

---

# 8. Tool

Tool 表示：

```text
ToolSpec
+
Executable
```

建议接口：

```python
class Tool(Protocol):

    @property
    def spec(self) -> ToolSpec:
        ...

    async def execute(
        self,
        inputs: dict[ArtifactKey, Any],
    ) -> dict[ArtifactKey, Any]:
        ...
```

要求：

```text
execute 输入
=
spec.consumes

execute 输出
=
spec.produces
```

Runtime 必须验证输出。

---

# 9. Python Tool 定义方式

Phase 1 推荐优先支持 decorator。

例如：

```python
@tool(
    consumes=[OrderId],
    produces=[Order],
)
async def get_order(
    order_id: OrderId,
) -> Order:
    ...
```

或者多输出：

```python
@tool(
    consumes=[Order],
    produces=[User, Payment],
)
async def split_order(
    order: Order,
) -> tuple[User, Payment]:
    ...
```

但是为了降低 MVP 复杂度：

> Phase 1 第一版建议只允许单输出 Tool。

即：

```text
N inputs
→
1 output
```

确认稳定后再加入多输出。

---

# 10. Tool Naming

默认 Tool Name 使用函数名：

```python
get_order
check_refund
refund_order
```

允许显式覆盖：

```python
@tool(
    name="mysql_get_order",
    consumes=[OrderId],
    produces=[Order],
)
```

Registry 中：

```text
Tool name 必须唯一
```

重复注册必须抛错。

---

# 11. ToolRegistry

职责仅包括：

```text
Register Tool
Get Tool
List Tool
Find Producers
```

推荐接口：

```python
class ToolRegistry:

    def register(self, tool: Tool) -> None:
        ...

    def get(self, name: str) -> Tool:
        ...

    def all(self) -> list[Tool]:
        ...

    def producers_of(
        self,
        artifact: ArtifactKey,
    ) -> list[Tool]:
        ...
```

Registry 不负责：

```text
Graph Planning
Execution
Provider Selection Strategy
```

---

# 12. Registry 内部索引

不能每次通过：

```text
for tool in all_tools
```

查找 producer。

Registry 建立：

```python
_tools_by_name: dict[str, Tool]

_producers_by_artifact:
    dict[ArtifactKey, list[Tool]]
```

例如：

```text
Order
    ↓
[
    mysql_get_order,
    mock_get_order
]
```

---

# 13. Dependency Edge

定义：

```python
@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    artifact: ArtifactKey
```

例如：

```text
get_order
    │
    │ Order
    ▼
check_refund
```

表示：

```python
DependencyEdge(
    source="get_order",
    target="check_refund",
    artifact=ArtifactKey(Order),
)
```

---

# 14. Dependency Graph

Graph 的 Node：

```text
Tool
```

Graph 的 Edge：

```text
Tool A produces X
AND
Tool B consumes X
```

则：

```text
A → B
```

Phase 1：

```text
Graph = Directed Graph
```

---

# 15. Graph Builder

核心算法：

```python
for consumer in tools:

    for consumed_artifact in consumer.consumes:

        producers = registry.producers_of(
            consumed_artifact
        )

        for producer in producers:

            if producer != consumer:
                add_edge(
                    producer,
                    consumer,
                    consumed_artifact,
                )
```

时间复杂度不作为 Phase 1 主要问题。

---

# 16. Graph Builder 必须防止 Self Edge

例如：

```python
normalize_order

consumes:
    Order

produces:
    Order
```

不得自动生成：

```text
normalize_order
      ↺
```

Phase 1：

```text
source == target
```

直接跳过。

---

# 17. Cycle

Phase 1 最终 ExecutionPlan 必须是 DAG。

但完整 Dependency Graph 允许存在潜在 Cycle。

例如：

```text
A produces X consumes Y
B produces Y consumes X
```

Graph：

```text
A → B
↑   ↓
└───┘
```

Builder 可以正常构建。

但：

> Planner 不能生成带 Cycle 的执行计划。

发现 Cycle 必须：

```text
raise CyclicDependencyError
```

---

# 18. Goal

Phase 1 不处理自然语言。

Goal 直接定义目标 Artifact：

```python
@dataclass(frozen=True)
class Goal:
    produces: ArtifactKey
```

调用：

```python
Goal(
    produces=ArtifactKey(RefundResult)
)
```

意思是：

> 找到能够生产 RefundResult 的执行路径。

---

# 19. Initial Inputs

Planner 必须知道：

> 哪些 Artifact 会由用户 / Runtime 初始提供。

例如：

```text
OrderId
```

用户直接输入。

因此：

```python
planner.plan(
    goal=Goal(RefundResult),
    available_inputs={
        ArtifactKey(OrderId),
    },
)
```

这些 Artifact 不需要寻找 Producer。

---

# 20. 最关键的 Planning 定义

Planning 问题定义为：

给定：

```text
Goal Artifact G
Initial Artifact Set I
Tool Set T
```

求：

```text
一个 Tool 子集 S
```

满足：

```text
执行 S 后可以产生 G
```

且 S 尽可能小。

Phase 1 不要求解决严格全局最优搜索。

只需要：

> 在简单 priority 策略下得到确定性的最小依赖路径。

---

# 21. Backward Planner

Planner 从：

```text
Goal Artifact
```

开始反向寻找 Producer。

伪代码：

```python
resolve(artifact):

    if artifact in available_inputs:
        return

    producers = registry.producers_of(artifact)

    if not producers:
        raise MissingProducerError

    producer = select_provider(producers)

    add producer to plan

    for dependency in producer.consumes:
        resolve(dependency)
```

最后得到所有必要 Tool。

---

# 22. 示例

注册：

```text
get_order

OrderId
↓
Order
```

```text
get_refund_policy

PolicyId
↓
RefundPolicy
```

```text
check_refund

Order + RefundPolicy
↓
RefundDecision
```

```text
refund_order

Order + RefundDecision
↓
RefundResult
```

Goal：

```text
RefundResult
```

Available Inputs：

```text
OrderId
PolicyId
```

反向：

```text
RefundResult
      ↑
refund_order
      ↑
Order + RefundDecision
 ↑                ↑
get_order     check_refund
                  ↑
          Order + RefundPolicy
                      ↑
             get_refund_policy
```

得到：

```text
get_order
get_refund_policy
check_refund
refund_order
```

---

# 23. Provider Selection

例如：

```text
mysql_get_order
mock_get_order
```

都产生：

```text
Order
```

Phase 1 使用简单规则：

```text
priority 越大优先级越高
```

例如：

```python
mysql_get_order.priority = 100
mock_get_order.priority = 10
```

则选择：

```text
mysql_get_order
```

---

# 24. Provider Tie

如果：

```text
priority 完全相同
```

必须保证 deterministic。

建议：

```text
priority DESC
name ASC
```

例如：

```text
a_get_order
b_get_order
```

优先：

```text
a_get_order
```

不要依赖：

```text
dict insertion order
```

作为规划语义。

---

# 25. 一个关键问题：Provider 本身可能不可满足

例如：

```text
Provider A

SecretToken
↓
Order
priority = 100
```

```text
Provider B

OrderId
↓
Order
priority = 50
```

当前只有：

```text
OrderId
```

如果单纯选最高优先级，会选到：

```text
Provider A
```

然后 Planning 失败。

因此 Planner 不能简单：

```text
先选最高 priority
再解析
```

必须：

```text
依次尝试 Candidate Provider
```

---

# 26. Provider Resolution Algorithm

候选：

```text
priority DESC
name ASC
```

逐个尝试：

```python
for producer in candidates:

    try:
        resolve(producer.dependencies)
        return producer

    except MissingDependency:
        rollback temporary plan
        continue
```

如果所有 Provider 均无法满足：

```text
raise UnsatisfiedDependencyError
```

这一点属于 Phase 1 必须实现。

---

# 27. Planning Context

Backward Search 必须维护：

```text
resolved_artifacts
selected_tools
resolving_artifacts
```

例如：

```python
class PlanningContext:
    resolved_artifacts: set[ArtifactKey]
    selected_tools: dict[str, Tool]
    resolving_artifacts: set[ArtifactKey]
```

其中：

```text
resolving_artifacts
```

用于发现递归 Cycle。

---

# 28. Cycle Detection

例如：

```text
A requires B
B requires A
```

解析：

```text
resolve(A)

A added to resolving

resolve(B)

B added to resolving

resolve(A)
```

发现：

```text
A already resolving
```

抛：

```text
CyclicDependencyError
```

错误信息必须包含依赖链。

例如：

```text
Cyclic dependency detected:

Order
→ Payment
→ Order
```

---

# 29. ExecutionPlan

Planner 的输出不能直接是：

```text
list[Tool]
```

必须定义独立模型。

例如：

```python
@dataclass(frozen=True)
class ExecutionNode:
    tool_name: str

@dataclass(frozen=True)
class ExecutionPlan:
    nodes: tuple[ExecutionNode, ...]
    edges: tuple[DependencyEdge, ...]
    goal: ArtifactKey
```

后续 Phase 可以扩展：

```text
Policy Decision
Cost
Provider Explanation
Trace Metadata
```

而不污染 Planner API。

---

# 30. ExecutionPlan 必须独立于 Runtime

核心约束：

```text
Planning
≠
Execution
```

必须支持：

```python
plan = planner.plan(...)

print(plan)

validate(plan)

await runtime.execute(plan)
```

不能：

```python
planner.run(...)
```

直接边规划边调用 Tool。

---

# 31. Topological Sort

Planner 完成子图后：

```text
ExecutionPlan
```

需要拥有合法拓扑顺序。

例如：

```text
A ──┐
    ↓
    C → D
    ↑
B ──┘
```

合法顺序：

```text
A
B
C
D
```

或者：

```text
B
A
C
D
```

Phase 1 为了保证 deterministic：

当多个 Node 同时可执行时：

```text
tool name ASC
```

排序。

---

# 32. ExecutionState

Runtime 使用统一状态存储 Artifact。

```python
class ExecutionState:

    def put(
        self,
        artifact: ArtifactKey,
        value: Any,
    ) -> None:
        ...

    def get(
        self,
        artifact: ArtifactKey,
    ) -> Any:
        ...

    def contains(
        self,
        artifact: ArtifactKey,
    ) -> bool:
        ...
```

初始化：

```python
state = ExecutionState(
    initial={
        ArtifactKey(OrderId): OrderId("123")
    }
)
```

---

# 33. Runtime Execution

Runtime 按拓扑顺序执行：

```python
for node in plan.nodes:

    tool = registry.get(node.tool_name)

    inputs = {
        artifact: state.get(artifact)
        for artifact in tool.spec.consumes
    }

    outputs = await tool.execute(inputs)

    validate_outputs(tool, outputs)

    state.update(outputs)
```

最后：

```python
return state.get(plan.goal)
```

---

# 34. Runtime 不允许隐式重新规划

如果 Runtime 发现：

```text
Tool dependency missing
```

必须直接失败。

禁止：

```text
Runtime 临时寻找另一个 Tool
```

因为：

```text
Planner
```

负责计划，

```text
Runtime
```

负责执行。

否则两层职责会混合。

---

# 35. Input Validation

Tool 执行前必须检查：

```text
spec.consumes
```

全部存在于 State。

否则：

```text
raise MissingRuntimeInputError
```

错误至少包括：

```text
tool
missing artifact
```

---

# 36. Output Validation

Tool 返回后必须验证：

```text
声明 produces Order
```

实际必须返回：

```text
Order
```

否则：

```text
raise InvalidToolOutputError
```

禁止 silently accept。

---

# 37. Phase 1 数据覆盖策略

Phase 1 禁止两个 Tool 在同一个 ExecutionPlan 中生产相同 Artifact。

例如：

```text
A → Order
B → Order
```

如果最终 Plan 同时包含 A 和 B：

```text
raise ArtifactConflictError
```

原因：

```text
ExecutionState
```

当前以：

```text
ArtifactKey
```

作为唯一 key。

未来如果需要：

```text
Named Artifact
Version
Namespace
```

放到后续 Phase。

---

# 38. 同一 Artifact 多 Provider 与冲突的区别

合法：

```text
mysql_get_order ─┐
                 ├─ candidate provider
mock_get_order ──┘
```

Planner 最终只选择其中一个。

非法：

```text
mysql_get_order
        ↓
       Order

mock_get_order
        ↓
       Order
```

两者同时进入同一个 Plan。

---

# 39. Error Model

Phase 1 必须建立自己的异常体系。

建议：

```python
class GraphRuntimeError(Exception):
    pass
```

子类：

```text
ToolRegistrationError
DuplicateToolError

MissingProducerError
UnsatisfiedDependencyError
CyclicDependencyError

InvalidExecutionPlanError
ArtifactConflictError

MissingRuntimeInputError
InvalidToolOutputError
ToolExecutionError
```

不要直接向调用方暴露：

```text
KeyError
ValueError
RuntimeError
```

作为核心业务错误。

---

# 40. ToolExecutionError

Tool 自己执行异常：

```python
try:
    output = await tool.execute(...)
except Exception as exc:
    raise ToolExecutionError(
        tool_name=...
    ) from exc
```

必须保留：

```text
exception chaining
```

方便定位原始错误。

---

# 41. Async First

Phase 1 Runtime API 统一：

```python
async
```

原因：

未来 Tool 大概率来自：

```text
Database
HTTP
MCP
LLM
RAG
```

因此 Runtime 直接设计为 async。

同步 Tool 可以由 Adapter 包装。

---

# 42. Phase 1 暂不实现并行执行

即使：

```text
A ──┐
    ↓
    C
    ↑
B ──┘
```

理论上：

```text
A
B
```

可以并行。

Phase 1 暂时顺序执行：

```text
A
B
C
```

Phase 3/5 再实现并发调度。

核心目标先验证：

```text
Graph correctness
```

而不是吞吐。

---

# 43. 推荐项目结构

Phase 1 推荐：

```text
src/
└── capability_runtime/
    │
    ├── core/
    │   ├── artifact.py
    │   ├── tool.py
    │   └── errors.py
    │
    ├── registry/
    │   └── tool_registry.py
    │
    ├── graph/
    │   ├── models.py
    │   └── builder.py
    │
    ├── planner/
    │   ├── goal.py
    │   ├── planner.py
    │   └── plan.py
    │
    ├── runtime/
    │   ├── state.py
    │   └── executor.py
    │
    └── decorators.py
```

测试：

```text
tests/
├── unit/
│   ├── test_registry.py
│   ├── test_graph_builder.py
│   ├── test_planner.py
│   ├── test_state.py
│   └── test_runtime.py
│
└── integration/
    └── test_refund_workflow.py
```

---

# 44. 模块依赖方向

严格保持：

```text
core
 ↑
registry
 ↑
graph
 ↑
planner

core
 ↑
runtime
```

更准确地：

```text
core
├── registry
├── graph
├── planner
└── runtime
```

禁止：

```text
core → planner
core → runtime
```

核心模型不能反向依赖上层。

---

# 45. 第一阶段 Demo

建议固定使用退款场景作为 Integration Demo。

Artifact：

```python
@dataclass(frozen=True)
class OrderId:
    value: str


@dataclass(frozen=True)
class PolicyId:
    value: str


@dataclass(frozen=True)
class Order:
    id: str
    amount: float


@dataclass(frozen=True)
class RefundPolicy:
    max_amount: float


@dataclass(frozen=True)
class RefundDecision:
    allowed: bool


@dataclass(frozen=True)
class RefundResult:
    success: bool
```

---

# 46. Demo Tools

```text
get_order

OrderId
↓
Order
```

```text
get_refund_policy

PolicyId
↓
RefundPolicy
```

```text
check_refund

Order
+
RefundPolicy
↓
RefundDecision
```

```text
refund_order

Order
+
RefundDecision
↓
RefundResult
```

额外加入两个无关工具：

```text
get_user
send_email
```

用来验证 Planner 剪枝。

---

# 47. Demo 完整 Graph

完整系统：

```text
get_order ──────────────┐
                        │
                        ▼
                  check_refund
                        ▲
                        │
get_refund_policy ──────┘
                        │
                        ▼
                  refund_order


get_user
   ↓
send_email
```

Goal：

```text
RefundResult
```

Planner 必须返回：

```text
get_order
get_refund_policy
check_refund
refund_order
```

不得包含：

```text
get_user
send_email
```

---

# 48. Unit Test — Registry

至少包括：

```text
register tool success
duplicate name rejected
get existing tool
get nonexistent tool
find producer
multiple producers
```

---

# 49. Unit Test — Graph Builder

至少包括：

### Test 1

```text
A produces X
B consumes X
```

得到：

```text
A → B
```

---

### Test 2

```text
A produces X
B consumes Y
```

不得建立 Edge。

---

### Test 3

```text
A consumes X
A produces X
```

不得建立 self edge。

---

### Test 4

多个 consumer：

```text
A → X

B consumes X
C consumes X
```

得到：

```text
A → B
A → C
```

---

# 50. Unit Test — Planner

必须覆盖：

### Test 1：Single Tool

```text
A
Input → Result
```

返回：

```text
[A]
```

---

### Test 2：Linear Dependency

```text
A → B → C
```

Goal C 输出。

返回：

```text
A
B
C
```

---

### Test 3：Branch Dependency

```text
A ─┐
   ↓
   C → D
   ↑
B ─┘
```

返回全部四个必要 Tool。

---

### Test 4：Pruning

完整 Graph：

```text
A → B → C

X → Y
```

Goal：

```text
C
```

只返回：

```text
A
B
C
```

---

### Test 5：Missing Producer

```text
B requires X
```

系统没有任何 Tool 生产 X。

且 X 不属于 initial input。

必须抛：

```text
MissingProducerError
```

---

### Test 6：Cycle

```text
A requires Y produces X
B requires X produces Y
```

必须抛：

```text
CyclicDependencyError
```

---

### Test 7：Provider Priority

```text
A produces X priority=100
B produces X priority=10
```

选择：

```text
A
```

---

### Test 8：Unreachable High Priority Provider

```text
A:
requires Secret
produces X
priority=100

B:
requires Input
produces X
priority=10
```

只有：

```text
Input
```

可用。

必须选择：

```text
B
```

而不是 Planning 失败。

---

# 51. Unit Test — Runtime

至少覆盖：

```text
initial state
tool input injection
artifact propagation
multiple dependency input
goal result retrieval
missing input
invalid output
tool exception wrapping
```

---

# 52. Integration Test

完整测试：

```python
plan = planner.plan(
    Goal(RefundResult),
    available_inputs={
        OrderId,
        PolicyId,
    },
)
```

断言：

```text
Plan Tools:

get_order
get_refund_policy
check_refund
refund_order
```

然后：

```python
result = await runtime.execute(
    plan,
    inputs={
        OrderId: OrderId("001"),
        PolicyId: PolicyId("default"),
    },
)
```

最终：

```text
RefundResult(success=True)
```

---

# 53. Plan Explain

Phase 1 应提供一个非常简单的：

```python
plan.explain()
```

输出类似：

```text
Goal:
RefundResult

Selected tools:

1. get_order
   requires: OrderId
   produces: Order

2. get_refund_policy
   requires: PolicyId
   produces: RefundPolicy

3. check_refund
   requires:
     - Order
     - RefundPolicy
   produces:
     RefundDecision

4. refund_order
   requires:
     - Order
     - RefundDecision
   produces:
     RefundResult
```

这是后续可解释性的基础。

---

# 54. Graph Inspect

Graph 应支持最基本的调试能力：

```python
graph.nodes()
graph.edges()
graph.predecessors(tool_name)
graph.successors(tool_name)
```

不需要 Graph UI。

---

# 55. 是否依赖 NetworkX

Phase 1 推荐：

> 不将 NetworkX 暴露为核心领域模型。

可以内部使用，也可以不用。

考虑 MVP 实现规模较小，建议直接维护：

```python
nodes: dict[str, Tool]

incoming:
dict[str, list[DependencyEdge]]

outgoing:
dict[str, list[DependencyEdge]]
```

原因：

核心 Graph 数据结构非常简单。

避免项目从第一版就对 NetworkX 形成强依赖。

---

# 56. Public API

Phase 1 对外 API 应尽量少。

期望最终主要暴露：

```python
from capability_runtime import (
    tool,
    ToolRegistry,
    DependencyGraphBuilder,
    Planner,
    Goal,
    Runtime,
)
```

内部实现类不应该全部暴露。

---

# 57. 开发顺序

严格按照以下顺序实现。

## Step 1

核心类型：

```text
ArtifactKey
ToolSpec
Tool
Errors
```

---

## Step 2

```text
@tool decorator
```

让普通 Python async function 转换成 Tool。

---

## Step 3

```text
ToolRegistry
```

完成 Tool 注册与 Producer Index。

---

## Step 4

```text
DependencyGraph
DependencyGraphBuilder
```

完成自动建图。

---

## Step 5

```text
Goal
ExecutionPlan
```

只建立数据结构。

---

## Step 6

```text
Backward Planner
```

完成：

```text
Goal → Subgraph
```

---

## Step 7

加入：

```text
Cycle Detection
Provider Selection
Rollback
```

---

## Step 8

```text
ExecutionState
Runtime
```

完成顺序执行。

---

## Step 9

```text
plan.explain()
graph.inspect()
```

增加 Debug 能力。

---

## Step 10

完成：

```text
refund integration demo
```

---

# 58. 每个 Step 的提交原则

建议一个 Step 对应一个独立 PR 或 commit group。

禁止：

```text
一次 PR 同时实现
Graph + Planner + Runtime + MCP
```

优先：

```text
PR 1 core models
PR 2 registry
PR 3 graph
PR 4 planner
PR 5 runtime
PR 6 integration demo
```

便于验证架构方向。

---

# 59. 代码质量要求

Phase 1 所有核心代码：

```text
必须有类型标注
```

建议：

```text
Python >= 3.12
```

数据对象优先：

```text
dataclass
```

暂时不要为了 Schema 引入大量 Pydantic。

原因：

当前模型主要用于：

```text
internal runtime
```

不是：

```text
HTTP boundary
```

---

# 60. 禁止过度抽象

Phase 1 禁止提前引入：

```text
AbstractGraphProvider
UniversalToolAdapter
CapabilityResolverFactory
ExecutionBackendManager
GraphCompilerPluginSystem
```

除非 Phase 1 已经存在两个真实实现需要统一接口。

原则：

> 第二个实现出现之前，不为第二个实现抽象。

---

# 61. Logging

Phase 1 可以使用标准：

```python
logging
```

记录：

```text
tool registered
graph built
planning started
provider selected
tool execution started
tool execution completed
```

但 Observability 不是本阶段重点。

---

# 62. Determinism

相同：

```text
Registry
Goal
Initial Inputs
```

必须产生相同：

```text
ExecutionPlan
```

因此所有存在多解的位置必须明确排序规则。

Phase 1 默认：

```text
Provider:
priority DESC
name ASC

Topological Ready Queue:
name ASC
```

---

# 63. Planner 必须是纯规划

对：

```python
planner.plan(...)
```

的调用：

不得：

```text
执行 Tool
访问数据库
调用 LLM
访问网络
修改外部状态
```

Planner 只处理：

```text
metadata
graph
goal
available inputs
```

因此 Planning 可以安全重复执行。

---

# 64. Phase 1 最终使用体验

理想使用代码：

```python
registry = ToolRegistry()

registry.register(get_order)
registry.register(get_refund_policy)
registry.register(check_refund)
registry.register(refund_order)
registry.register(get_user)
registry.register(send_email)

graph = DependencyGraphBuilder(
    registry
).build()

planner = Planner(
    registry=registry,
    graph=graph,
)

plan = planner.plan(
    goal=Goal.of(RefundResult),
    available_inputs={
        ArtifactKey.of(OrderId),
        ArtifactKey.of(PolicyId),
    },
)

print(plan.explain())

runtime = Runtime(
    registry=registry,
)

result = await runtime.execute(
    plan,
    inputs={
        ArtifactKey.of(OrderId): OrderId("123"),
        ArtifactKey.of(PolicyId): PolicyId("default"),
    },
)

assert result.success
```

---

# 65. Phase 1 Definition of Done

Phase 1 完成必须同时满足以下条件。

## Core

* [ ] ToolSpec 可定义 consumes / produces
* [ ] Python Tool 可注册
* [ ] Registry 可以索引 Artifact Producer
* [ ] Graph Builder 可以自动产生依赖 Edge
* [ ] Goal 可以定义目标 Artifact
* [ ] Planner 可以反向解析依赖
* [ ] Planner 可以删除无关 Tool
* [ ] Planner 支持多 Provider
* [ ] Planner 可以检测 Cycle
* [ ] Planner 输出 ExecutionPlan
* [ ] ExecutionPlan 为 DAG
* [ ] Runtime 可以执行 DAG
* [ ] Artifact 可以正确传播
* [ ] Runtime 可以返回目标 Artifact

## Quality

* [ ] 所有核心模块有单元测试
* [ ] Refund Demo 集成测试通过
* [ ] 错误使用项目自定义异常
* [ ] Planner 行为 deterministic
* [ ] Runtime 和 Planner 完全分离
* [ ] 无 LLM 依赖
* [ ] 无 MCP 依赖
* [ ] 无 Web Framework 依赖

---

# 66. Phase 1 成功标准

最终必须证明以下场景成立：

系统存在：

```text
20 Tools
```

用户提供：

```text
OrderId
PolicyId
```

目标：

```text
RefundResult
```

Runtime 可以自动得到：

```text
get_order
        │
        ├────────────┐
        │            ▼
        │      check_refund
        │            ▲
        │            │
get_refund_policy ───┘
                     │
                     ▼
                refund_order
```

并执行得到：

```text
RefundResult
```

同时：

```text
get_user
send_email
search_web
generate_report
...
```

等无关 Tool 不进入 ExecutionPlan。

---

# 67. Phase 1 最核心的验收问题

完成代码后，只问四个问题：

### 1.

新增一个：

```text
A produces X
```

以及：

```text
B consumes X
```

是否完全不修改 Graph 代码就可以自动出现：

```text
A → B
```

### 2.

新增一个 Provider 后，是否完全不修改既有 Pipeline 即可形成新的候选执行路径？

### 3.

给一个 Goal 后，系统是否只选择完成 Goal 必需的 Tool？

### 4.

LLM 完全不存在的情况下，这套系统是否仍能完成规划和执行？

如果四个答案全部为：

```text
Yes
```

则 Phase 1 核心假设验证成功。

---

# 68. Phase 1 结束后的唯一下一步

Phase 1 验证成功后，再进入 Phase 2：

```text
Typed Dependency Graph
            ↓
Typed Capability Graph
```

Phase 2 再正式加入：

```text
Capability
Layer
Effect
Risk
Permission
Policy
```

届时 Edge 将从：

```text
produces / consumes
```

升级为：

```text
Type Compatibility
+
Capability Compatibility
+
Layer Constraint
+
Policy Validation
```

在此之前，不提前实现这些能力。
