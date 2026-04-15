# No-PDB EPF + DSUUU EWMA 设计文档

## 背景

当前调度排序使用 `EpfRankingPolicy`，核心权重形式为：

- 基础项：`inst_rate / avg_rate`
- 时延项：`HOL / (PDB - HOL)`
- 当 `HOL >= PDB` 时，直接返回固定高权重

在现有实现里，`avg_rate` 并不是长期平均速率，而是最近一次服务时直接用 `bits_sent` 覆盖；同时，所有业务都必须携带 `pdb_ms`，导致“不设置 PDB”的业务只能通过配置一个极大 PDB 值来近似表达。

这带来两个问题：

1. `avg_rate` 过于瞬时，导致 PF/EPF 分母波动过大，不像长期平均吞吐。
2. 无 PDB 业务仍然被迫参与 `HOL / (PDB - HOL)` 权重，语义不干净，也不符合工程真实口径。

## 问题定义

本次设计要解决的是：

- 如何让 `avg_rate` 更像长期平均速率，而不是最近一次发包量。
- 如何让“无 PDB”业务回到纯 EPF 逻辑，不再被 deadline 权重影响。
- 同时保持“有 PDB”业务的现有时延敏感权重形式不变，以便和真实场景、既有结果继续对齐。

## 目标

- `avg_rate` 改为按 `DSUUU` 周期更新的 EWMA 平均速率。
- 即使 UE 在某个周期没有被服务，也要参与更新，等价于该周期速率为 `0`。
- 无 PDB 业务排序时仅使用 `inst_rate / avg_rate`。
- 有 PDB 业务继续沿用当前保守口径，即保留 `HOL / (PDB - HOL)` 及 `HOL >= PDB` 时的强优先处理。
- 不在本次改动中引入 GBR 相关排序逻辑。

## 非目标

- 不重写整个回插策略。
- 不修改 `business_aware_constrained_insert` 的“队尾安全性”判定逻辑。
- 不在本次改动中把 deadline 权重从硬形式改成 soft boost。
- 不在本次改动中引入中心保护线、PRB 保底或新的系统效用函数。

## 设计决策

### 1. `avg_rate` 改为按 `DSUUU` 周期统计

当前仿真只在 `D` 和 `S` 控制相位使用排序值，因此 `avg_rate` 也应该和控制决策周期对齐，而不是按单个 `U-slot` 即时抖动。

新的定义为：

- 每个 `DSUUU` 周期统计 UE 在该周期内的总 `served_bits`
- 将其换算为该周期平均速率：
  - `cycle_rate_bps = served_bits_in_cycle / cycle_duration_seconds`
- 用 EWMA 更新：
  - `avg_rate_next = beta * avg_rate_prev + (1 - beta) * cycle_rate_bps`

其中：

- `cycle_duration_seconds = len(tdd_pattern) * slot_duration_ms / 1000`
- 默认 `tdd_pattern = DSUUU`，即一个周期为 `5 ms`

### 2. 无服务周期也更新为 0 速率

若某个 UE 在一个完整 `DSUUU` 周期内没有获得任何服务：

- `served_bits_in_cycle = 0`
- `cycle_rate_bps = 0`
- 仍然执行一次 EWMA 更新

这样可以让长期未被服务的 UE 的 `avg_rate` 自然回落，更符合 PF/EPF 中“长期公平性”的直觉，也避免历史高吞吐用户因为长时间不更新而一直背着过大的分母。

### 3. 无 PDB 用户使用纯 EPF

对于无 PDB 业务，排序权重定义为：

- `score = inst_rate / avg_rate`

其中：

- `inst_rate` 沿用当前实现语义，即当前无线状态下的 `bits_per_prb`
- `avg_rate` 使用新的 `DSUUU` 周期 EWMA 平均速率

这类业务的解释是：

- 不承诺 deadline
- 不参与 deadline urgency
- 仅在频谱效率与长期公平性之间做 PF/EPF 折中

### 4. 有 PDB 用户保留当前 deadline 权重形式

为了和现网口径、已有实验结果保持可比性，有 PDB 用户的排序权重仍采用当前保守形式：

- 若 `HOL >= PDB`，返回当前的强优先高权重
- 否则：
  - `score = (inst_rate / avg_rate) * HOL / (PDB - HOL)`

这里不对公式形式做重构，也不引入新的 bounded boost。

本次改动只做一件事：

- 将“有 PDB 的用户”和“无 PDB 的用户”从排序逻辑上明确分开

### 5. GBR 与本次排序逻辑解耦

本次设计明确不把 GBR 混入无 PDB 业务的基础排序定义中。

也就是说：

- 无 PDB 不等于看 GBR
- 无 GBR 不等于失去排序资格
- 本次改动后，best-effort 业务的基础逻辑就是纯 EPF

如果后续需要做 GBR-aware 调度，应作为独立增强项，在本次口径稳定后再设计。

## 配置与数据模型变化

### 1. `pdb_ms` 需要支持“无 PDB”表达

当前模型把 `pdb_ms` 当作必填整数。本次设计要求能够明确表达“无 PDB”，建议支持以下语义之一：

- `pdb_ms = null`
- 或增加显式字段表示该业务不参与 deadline 排序

本次设计推荐优先采用 `pdb_ms = null`，因为它和现有字段最接近，也最容易让排序逻辑按“有/无 PDB”分流。

### 2. 增加 `avg_rate` 的 EWMA 参数

需要引入一个可配置或默认固定的 EWMA 平滑系数，例如：

- `avg_rate_ewma_beta`

该参数控制历史平均速率对新周期速率的记忆深度。

本次设计不强行规定最终默认值，但要求：

- 参数有明确默认值
- 测试和报告中写清楚该值

### 3. 增加周期内累计服务量状态

为了支持按 `DSUUU` 周期更新 `avg_rate`，需要在仿真运行过程中为每个 UE 维护：

- 当前周期累计 `served_bits`

并在每个周期结束时统一完成：

- 速率换算
- EWMA 更新
- 周期计数清零

## 排序逻辑定义

### 无 PDB

- `score = inst_rate / avg_rate`

### 有 PDB

- 若 `HOL >= PDB`：
  - 返回当前强优先高权重
- 否则：
  - `score = (inst_rate / avg_rate) * HOL / (PDB - HOL)`

### 共同规则

- `inst_rate` 仍取当前无线状态对应的 `bits_per_prb`
- `avg_rate` 需设置合理下限，避免除零或极端爆炸
- 排序只在 `D/S` 控制相位发生，因此使用的 `avg_rate` 是上一完整周期更新后的值

## 预期行为变化

### 无 PDB 业务

- 不再因为伪造的大 PDB 值而带入 deadline bias
- 排序更接近真实 PF/EPF
- `avg_rate` 平滑后，排序波动会比当前实现更小

### 有 PDB 业务

- deadline urgency 机制保持不变
- 但由于 `avg_rate` 更平滑，最终权重也会比当前实现更稳定

### 系统层面

- 相比当前实现，无 PDB 背景业务的行为解释会更清晰
- 实验报告里可以明确区分：
  - best-effort 排序行为
  - deadline-sensitive 排序行为

## 风险与权衡

### 1. 与历史结果的数值偏移

即使有 PDB 用户的 urgency 公式不变，仅仅因为 `avg_rate` 从“最近一次发送量”改成“周期 EWMA 速率”，结果也会发生变化。

这是预期内变化，不应被理解为 bug，而是排序基础量定义更合理后的自然结果。

### 2. `pdb_ms = null` 的兼容性

配置加载、模型定义、排序逻辑、报告生成都需要兼容无 PDB 语义。

需要特别检查：

- 旧配置仍然可运行
- 新配置不会在比较、格式化、导出时触发类型错误

### 3. 高权重 deadline 用户仍可能很强势

本次设计是保守改法，不触碰当前有 PDB 用户的强 deadline 权重。因此它不会解决所有“PDB 过强”的问题，只会先解决：

- 无 PDB 业务被错误 deadline 化
- `avg_rate` 过于瞬时

## 测试与验证要求

需要验证四类行为：

### 1. `avg_rate` 更新语义

- UE 在一个周期内有服务时，`avg_rate` 按周期速率做 EWMA
- UE 在一个周期内无服务时，`avg_rate` 也会向 `0` 速率方向更新
- 不再发生“每次发送后直接用本次 `bits_sent` 覆盖 `avg_rate`”

### 2. 无 PDB 排序语义

- 无 PDB 用户排序仅受 `inst_rate / avg_rate` 影响
- 不再访问 `HOL / (PDB - HOL)` 权重项

### 3. 有 PDB 排序兼容性

- 有 PDB 用户仍沿用当前 urgency 逻辑
- `HOL >= PDB` 的强优先语义保持一致

### 4. 配置兼容性

- 旧配置：继续支持 `pdb_ms` 为整数
- 新配置：支持无 PDB 表达
- CLI、报告、指标输出在两类配置下都能正常运行

## 推荐实施顺序

1. 先让配置与模型支持“无 PDB”表达
2. 再把 `avg_rate` 改为周期 EWMA 更新
3. 再调整排序逻辑分流：
   - 有 PDB
   - 无 PDB
4. 最后补测试与对比实验

## 结论

本次设计采取保守改法，目标不是重写调度器，而是先把两件最关键的语义理顺：

- `avg_rate` 必须是按 `DSUUU` 周期更新的平滑平均速率
- 无 PDB 业务必须回到纯 EPF，而不是继续隐含参与 deadline 权重

这样做既能保留当前有 PDB 场景与真实口径的可比性，也能让 best-effort 业务的行为解释更加工程真实。
