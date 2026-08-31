# Architecture Pivot

项目早期尝试过 `Artifact → Backward Planning → Minimal DAG`。该模型回答“为了得到目标类型需要哪些依赖”，但没有回答项目真正关心的问题：“在允许的工具组合空间里，哪些 Route 在真实业务中有效”。

当前架构因此改为：

```text
开发者声明 Layered Search Space
        ↓
Battlefield 探索业务 Route
        ↓
Trace 与多维 Evaluation
        ↓
Declared Topology 派生 Active Topology Versions
```

旧实现中保留的原则包括 Registry、Topology 与执行分离、async Tool、Schema Validation、自定义错误和确定性初始化；Artifact Goal、Producer Resolution、Backward Planner 与 Minimal DAG 不再属于主线。
