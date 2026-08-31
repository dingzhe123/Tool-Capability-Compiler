可行，而且我认为这个方向比传统的“Agent 拿到 30 个 tools 自己随便选”更适合作为一个真正的 **Agent Runtime / Pipeline 编排框架**。

但我会对你的想法做一个关键修正：

> **不要把它实现成严格的神经网络式 Layer，而应该实现成“分层的 Capability Graph（能力图）”。**

你说的“节点 + 层 + 剪枝 + 自动传播”本质上已经接近一个**可动态扩展的工具能力图**。

---

# 1. 先把你的想法抽象一下

例如现在有这些工具：

```text
RAGSearch
OrderQuery
UserQuery
WebSearch

UpdateOrder
SendEmail
CreateRefund
SendCoupon
```

传统 Agent 是：

```text
             Agent
               |
    -------------------------
    |     |       |        |
   RAG   DB     Email    Refund
```

LLM 每一步都从全部工具里选。

而你提出的是：

```text
Layer 1: READ

RAGSearch
OrderQuery
UserQuery
WebSearch

        ↓

Layer 2: PROCESS / DECISION

PolicyCheck
RefundEligibility
ContentGenerator
RiskCheck

        ↓

Layer 3: WRITE

UpdateOrder
CreateRefund
SendCoupon
SendEmail
```

并且并不是：

```text
READ 全连接 WRITE
```

而是：

```text
OrderQuery ───────→ CreateRefund
      │
      └───────────→ UpdateOrder

RAGSearch ────────→ PolicyCheck
                        │
                        ↓
                   CreateRefund

UserQuery ─────────→ SendCoupon

WebSearch ─────────→ ContentGenerator
                        │
                        ↓
                     SendEmail
```

这个模型已经非常有意思了。

它不是单纯的：

> Tool Registry

而是：

> **Capability Topology**

工具之间存在结构化的能力关系。

---

# 2. 但是 Read / Write 两层还不够

如果真做，我建议至少抽象成四类：

```text
Observe
   ↓
Transform
   ↓
Decide
   ↓
Act
```

对应：

| Layer     | 作用      | 示例                          |
| --------- | ------- | --------------------------- |
| Observe   | 获取事实    | RAG、SQL、WebSearch、API Query |
| Transform | 加工信息    | 聚合、抽取、排序、计算、解析              |
| Decide    | 做业务判断   | 权限判断、退款判断、策略选择、风控           |
| Act       | 产生外部副作用 | 发邮件、退款、修改订单、发消息             |

比单纯：

```text
Read
Write
```

更合理。

原因是有一大类工具既不是 Read，也不是 Write。

例如：

```text
calculate_price()
classify_intent()
check_refund_policy()
rank_documents()
generate_report()
```

它们其实是：

```text
pure computation
```

没有外部副作用。

这一层非常重要。

---

# 3. 真正有价值的不是 Layer，而是 Edge

你这个设计最有价值的其实不是：

```text
READ → WRITE
```

而是：

```text
Tool A 能不能把结果传给 Tool B
```

例如：

```python
get_order
```

输出：

```python
Order
```

而：

```python
create_refund
```

要求：

```python
RefundRequest
```

中间可能需要：

```text
get_order
   ↓
check_refund_eligibility
   ↓
build_refund_request
   ↓
create_refund
```

于是每一个 Tool 都可以声明：

```python
ToolSpec(
    name="get_order",
    layer="observe",
    input_type=OrderId,
    output_type=Order,
)
```

然后：

```python
ToolSpec(
    name="check_refund",
    layer="decide",
    input_type=Order,
    output_type=RefundDecision,
)
```

最后：

```python
ToolSpec(
    name="create_refund",
    layer="act",
    input_type=RefundDecision,
    output_type=RefundResult,
)
```

Runtime 自动得到：

```text
get_order
    ↓
check_refund
    ↓
create_refund
```

这就开始变得非常强了。

---

# 4. 这时候甚至不需要手工“连线”

这是我认为你这个想法最值得继续挖的地方。

假设工具注册：

```python
@tool(
    capability="order.read",
    produces=["Order"],
)
def get_order(...):
    ...
```

另一个：

```python
@tool(
    capability="refund.check",
    requires=["Order"],
    produces=["RefundDecision"],
)
def check_refund(...):
    ...
```

再一个：

```python
@tool(
    capability="refund.execute",
    requires=["RefundDecision"],
    produces=["RefundResult"],
    effect="write",
)
def refund(...):
    ...
```

Registry 注册以后自动构建：

```text
Order
  ↑
get_order
  ↓
check_refund
  ↓
RefundDecision
  ↓
refund
```

你添加一个新工具：

```python
@tool(
    capability="coupon.issue",
    requires=["User", "CouponPolicy"],
    produces=["CouponResult"],
    effect="write",
)
```

Graph Builder 自动去找：

```text
谁可以产生 User？
谁可以产生 CouponPolicy？
```

例如：

```text
get_user ──────────┐
                   ↓
                send_coupon
                   ↑
rag_coupon_policy ─┘
```

这就是你说的：

> 裂变式能力组装

而且这里已经不是比喻了。

它真的能够自动产生新的 Pipeline 组合。

---

# 5. 但不要“新增节点默认全量传播”

这里我会比较强烈地反对你原始设计中的这一点。

如果：

> 每新增一个 Tool，都默认允许传播给下一层所有 Node

最终会发生：

```text
N × M
```

式组合爆炸。

例如：

```text
50 read tools
30 processing tools
20 write tools
```

理论路径数量已经非常恐怖。

更加严重的是**安全问题**。

比如：

```text
get_user_profile
```

绝对不应该自动连接：

```text
delete_account
```

即使 input/output schema 恰好兼容。

所以应该反过来：

> **Schema Compatibility 决定“技术上能不能连接”，Capability Policy 决定“业务上允不允许连接”。**

即：

```text
Possible Edge
=
Type Compatible
AND
Capability Compatible
AND
Policy Allowed
```

---

# 6. 我建议给每个节点加 6 类 metadata

这是这个框架能不能真正跑起来的关键。

例如：

```python
ToolSpec(
    name="refund_order",

    layer="act",

    consumes={
        "Order",
        "RefundDecision",
    },

    produces={
        "RefundResult",
    },

    capability={
        "order.refund",
    },

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

至少应该有：

```text
1. consumes
2. produces
3. capability
4. effects
5. risk
6. permissions
```

然后才能自动推导：

```text
A → B
```

---

# 7. Layer 应该成为约束，而不是主要路由逻辑

例如：

```text
observe
transform
decide
act
```

正常情况下：

```text
observe → transform
observe → decide
transform → decide
decide → act
```

但不是绝对禁止：

```text
observe → act
```

例如：

```text
get_email_address
        ↓
send_verification_email
```

根本不需要 Decision。

所以 Layer 更像：

```text
architectural constraint
```

而不是：

```text
hard-coded execution sequence
```

也就是说：

```python
allowed_layer_edges = {
    "observe": {"transform", "decide", "act"},
    "transform": {"transform", "decide", "act"},
    "decide": {"act"},
    "act": set(),
}
```

而具体边：

```text
Tool A → Tool B
```

仍然由 capability / schema 决定。

---

# 8. 你的“剪枝”思想非常值得保留

这一部分甚至可以成为整个框架的核心。

用户说：

> 帮我退款订单 123

不要把：

```text
100 tools
```

给 Agent。

先做：

```text
Goal = refund(order_id)
```

然后从目标反向搜索。

比如目标工具：

```text
refund_order
```

需要：

```text
RefundDecision
Order
```

那么向前寻找 producer：

```text
refund_order
      ↑
check_refund_policy
      ↑
get_order
```

最终得到：

```text
Subgraph:

get_order
   ↓
check_refund_policy
   ↓
refund_order
```

此时真正交给 Agent 的可能只有：

```text
3 tools
```

而不是：

```text
整个系统 100 tools
```

这个设计非常重要。

---

# 9. 我甚至建议：不是“从上往下传播”，而是“从 Goal 反向编译”

这会比你的神经网络传播模型更好。

用户：

```text
我要给客户退款
```

首先识别：

```text
Goal:
    capability = order.refund
```

Runtime 找到：

```text
refund_order
```

然后看：

```text
requires:
    RefundDecision
```

继续找 producer：

```text
check_refund
```

它要求：

```text
Order
RefundPolicy
```

于是继续：

```text
get_order
get_refund_policy
```

最终编译：

```text
              get_order
                 │
                 ├─────────┐
                 ↓         │
           check_refund    │
                 ↑         │
                 │         │
       get_refund_policy   │
                 │         │
                 └────┬────┘
                      ↓
                 refund_order
```

这其实已经很像：

> **Agent Planner + Dependency Injection + Compiler**

三个东西的结合。

---

# 10. 这和 LLM Agent 的传统 Planner 有本质区别

传统：

```text
LLM:
我要退款。

Thought:
先查订单。

Tool:
get_order

Thought:
再查退款政策。

Tool:
search_policy

Thought:
应该能退款。

Tool:
refund
```

所有规划都依赖 LLM。

你的设计则可以变成：

```text
LLM:
我要退款。

↓ Goal Parser

order.refund

↓ Graph Compiler

get_order
get_refund_policy
check_refund
refund_order

↓ Executor

execute DAG
```

LLM 的职责从：

```text
Planner + Router + Executor
```

缩小成：

```text
Goal understanding
+
ambiguous decision making
```

而 Runtime 承担：

```text
tool dependency resolution
tool routing
permission check
data propagation
execution
```

这是一个明显更工程化的方向。

---

# 11. 甚至可以产生你之前 AgentHub 想解决的动态注册效果

你之前讨论过：

> 新业务加入 Skill / MCP / Tool 后，不希望每次手工修改 Pipeline。

这个架构正好可以解决这个问题。

例如业务团队只提交：

```python
class SendInvoiceTool:

    consumes = ["Order"]

    produces = ["InvoiceResult"]

    capabilities = ["invoice.send"]

    layer = "act"
```

注册：

```text
AgentHub.register(SendInvoiceTool)
```

系统重新计算 capability graph：

```text
get_order
    ↓
send_invoice
```

如果以后加：

```text
generate_invoice
```

```python
consumes = ["Order"]
produces = ["Invoice"]
```

以及：

```text
send_invoice
consumes = ["Invoice"]
```

Graph 又自动变成：

```text
get_order
    ↓
generate_invoice
    ↓
send_invoice
```

Pipeline 不需要人重新写。

这就真正具备了：

> **Plugin 化 Agent Pipeline**

---

# 12. 但是这里马上会出现一个非常有意思的问题：一个数据可能有多个 Producer

例如：

```text
UserProfile
```

可能由：

```text
mysql_get_user
crm_get_user
rag_get_user
```

产生。

那么 Graph：

```text
mysql_get_user ─┐
crm_get_user ───┼→ UserProfile → next node
rag_get_user ───┘
```

这时需要一个新的概念：

## Edge / Node scoring

例如：

```python
score =
    reliability * 0.3
  + latency * 0.2
  + cost * 0.2
  + freshness * 0.2
  + permission * 0.1
```

于是：

```text
Goal
 ↓
Graph Search
 ↓
候选 Pipeline
 ↓
Cost-based Planner
 ↓
选择执行路径
```

这已经有点数据库 Query Optimizer 的味道了。

---

# 13. 所以这个系统最终可能长成这样

```text
                    User Request
                         │
                         ▼
                  Intent / Goal Parser
                         │
                         ▼
                    Goal Schema
                         │
                         ▼
                Capability Registry
                         │
                         ▼
                  Graph Compiler
                         │
           ┌─────────────┼─────────────┐
           │             │             │
      Type Check    Policy Check    Risk Check
           │             │             │
           └─────────────┼─────────────┘
                         ▼
                   Candidate DAG
                         │
                         ▼
                    Graph Pruner
                         │
                         ▼
                  Execution Plan
                         │
                         ▼
                     Runtime
                         │
                  ┌──────┴──────┐
                  ▼             ▼
               Tool          Tool
                  │             │
                  └──────┬──────┘
                         ▼
                       State
```

这里：

```text
Tool Registry
```

已经不只是：

```python
dict[str, callable]
```

而是：

```text
Semantic Capability Registry
```

---

# 14. 最有价值的一点：Agent 不再拥有“工具”

这个架构里我甚至建议改变一个概念。

不是：

> Agent 有哪些 tools？

而是：

> Agent 有哪些 capabilities？

例如：

```yaml
agent:
  capabilities:
    - order.read
    - policy.read
    - refund.check
    - refund.execute
```

Runtime 再去解析：

```text
order.read
```

当前有哪些 provider：

```text
mysql_order_reader
erp_order_reader
mock_order_reader
```

于是：

```text
Agent
   ↓
Capability
   ↓
Tool Provider
```

类似：

```text
业务
↓
interface
↓
implementation
```

这其实就是依赖倒置。

---

# 15. MCP 在这里也会变得非常自然

例如 MCP Server 暴露：

```text
search_order
search_customer
refund_order
```

不要直接：

```text
register_mcp_tools()
```

而是转换成：

```text
MCP Tool
   ↓
Tool Adapter
   ↓
Capability Metadata
   ↓
Capability Graph
```

这样不管底层是：

```text
Python function
MCP
HTTP API
RPC
Workflow
另一个 Agent
```

在 Runtime 看来都是：

```text
Node
```

这非常漂亮。

---

# 16. 我会给这个架构一个明确定位

如果真的做成开源项目，不要描述为：

> 一个 Agent Pipeline 框架。

这个说法太普通。

我会定义成：

> **A typed capability graph runtime for composable AI agents.**

中文：

> **基于类型化能力图的智能体运行时。**

核心理念：

```text
Tool
不是孤立函数

Tool =
Capability
+ Contract
+ Effects
+ Policy
+ Dependency
```

系统自动：

```text
注册
    ↓
建图
    ↓
剪枝
    ↓
规划
    ↓
执行
```

---

# 17. 一个非常小的 V0.1 就足够验证

先不要上 LLM Planner、多 Agent、复杂工作流。

只做：

```text
Tool Registry
+
Typed IO
+
Capability
+
Layer
+
Auto Edge
+
Backward Planning
+
DAG Execution
```

例如只实现 6 个工具：

```text
get_user
get_order
get_refund_policy

check_refund

refund_order
send_email
```

验证：

```text
Goal:
refund_order
```

自动生成：

```text
get_order ──────┐
                ↓
get_policy → check_refund
                ↓
           refund_order
                ↓
            send_email
```

如果这个 prototype 跑起来，我认为这个方向就值得继续做。

---

你这个想法里，我认为真正值得抓住的不是“像神经网络一样逐层传播”，而是这三个东西：

```text
Tool → Node

输入/输出/能力 → Edge

Goal → Subgraph
```

一旦这三个抽象成立，**Pipeline 就不再需要人工编排，而可以变成“由工具能力图动态编译出来的执行计划”**。

这其实已经开始触碰一个挺有潜力的 Agent Runtime 架构了。
