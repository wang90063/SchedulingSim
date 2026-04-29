# Target Edge PDB Dominance Diagnostic 报告设计

## 背景

当前 `400KB` target edge 大包实验已经能看到两类现象：

1. `business_aware_constrained_insert` 能显著降低 target edge 大包的完成时延；
2. 中心用户平均吞吐在部分场景中稳定低于 `tail_append`，说明边缘保护策略带来了明显中心代价。

单看完成时延和中心吞吐，仍然不容易解释某一段时间到底是谁在主导调度：

- 是 target edge 用户因为无线条件、谱效项、平均吞吐项而自然排到前面；
- 还是因为 HOL 接近 PDB，PDB 时延压力项开始主导 EPF 排序；
- 或者 target edge 用户根本还没进入候选窗口，此时排序权重再高也没有用，真正主导的是 active queue 位置和回插策略。

因此，本轮不改调度策略，单独新增一个诊断报告，专门观察单个 target edge PDB 大包用户在每次 `D/S` 决策点中的队列位置、候选集内排序位置和 EPF 权重组成随时间的变化。

## 目标

本报告回答以下问题：

1. target edge 大包用户在 `tail_append` 和 `business_aware_constrained_insert` 下，何时进入前 `max_ue_per_slot` 候选窗口；
2. target edge 用户进入候选窗口后，候选集内 EPF 排序位置如何随时间变化；
3. EPF 权重中 `spectral_term = inst_rate / average_throughput` 与 `hol_factor = HOL / (PDB - HOL)` 哪个阶段更主导；
4. 两种策略下，`queue_limited`、`spectral_dominated`、`pdb_dominated`、`overdue_pdb_forced` 各阶段持续多久；
5. 用图形解释为什么某些阶段是谱效主导，某些阶段是 PDB 主导。

## 范围

本轮只覆盖一个干净的典型 case：

- target edge 大包：`400KB`
- edge PDB：`500 ms`
- 中心用户数：`63`
- 中心业务：`960 bit / every 6 slots`
- 资源：每个 U-slot `237 PRB`
- 对比策略：
  - `tail_append`
  - `business_aware_constrained_insert`

本轮明确不做：

- 不扫描多个 PDB；
- 不扫描多个包大小；
- 不改现有调度策略；
- 不引入新的中心前插或边缘降权机制；
- 不把该诊断混进现有 packet-size sensitivity 主报告。

## 核心诊断口径

### 1. 决策点粒度

当前仿真不是每个 `U` slot 重新排序，而是在每个周期的 `D` 和 `S` 阶段生成后续 `U` slot 的 plan。因此本报告按每次 `D/S` 决策点记录诊断数据。

每个决策点记录 target edge 用户在调度前的状态：

- 当前时间 `time_ms`
- 决策阶段 `phase = D | S`
- active queue 中的位置 `queue_rank`
- 是否进入候选窗口 `in_candidate_window`
- 候选集内 EPF 排序名次 `candidate_rank_epf`
- 候选集内纯谱效项排序名次 `candidate_rank_spectral_only`
- `inst_rate_bits_per_prb`
- `average_throughput`
- `spectral_term = inst_rate_bits_per_prb / max(average_throughput, 1.0)`
- `hol_ms`
- `pdb_ms`
- `pdb_slack_ms = pdb_ms - hol_ms`
- `hol_factor = hol_ms / max(1, pdb_ms - hol_ms)`
- `epf_weight`
- 阶段标签 `dominance_label`

`queue_rank` 和 `candidate_rank_*` 均使用 1-based rank，便于图上解释：`1` 表示最靠前。

### 2. 阶段判定

每个决策点按以下规则打标签：

- `not_pending`：target edge 大包尚未到达或已经完成；
- `queue_limited`：target edge 大包 pending，但没有进入前 `max_ue_per_slot` 候选窗口；
- `spectral_dominated`：target edge 进入候选窗口，且 `hol_factor < 1`，即 `HOL < PDB / 2`；
- `pdb_dominated`：target edge 进入候选窗口，且 `hol_factor >= 1`，即 `HOL >= PDB / 2`；
- `overdue_pdb_forced`：`HOL >= PDB`，此时现有 EPF 实现将 PDB 用户权重置为高值。

这套规则不是要精确证明数学上的唯一主导因子，而是给报告一个可解释、可复现的工程判别口径。

## 输出设计

新增独立输出目录：

```text
outputs/target_edge_pdb_dominance_diagnostic/
```

目录内输出：

```text
diagnostic_report.md
decision_trace.csv
decision_trace.json
queue_position_vs_time.png
epf_rank_vs_time.png
dominance_terms_vs_time.png
dominance_timeline.png
```

图形使用 `matplotlib` 生成 `png`。原因是本报告以图形可读性为优先，`queue rank`、`candidate rank`、阶段时间轴和双策略对比都更适合直接用成熟绘图库绘制；本轮允许安装依赖，因此不再强求零新增绘图依赖。

## 图形设计

### 图 1：Active Queue 位置随时间变化

文件：`queue_position_vs_time.png`

- 横轴：`time_ms`
- 纵轴：target edge 用户在 active queue 中的 `queue_rank`
- `1` 表示队头，数值越大表示越靠后
- 两条线：
  - `tail_append`
  - `business_aware_constrained_insert`
- `D` 和 `S` 决策点用不同 marker 或颜色深浅区分
- 加一条水平参考线：`max_ue_per_slot = 16`

解释重点：

- 曲线高于 `16` 时，target edge 还没进入候选窗口，是 `queue_limited`；
- 曲线低于或等于 `16` 后，才需要进一步看候选集内排序与 EPF 权重。

### 图 2：候选集内 EPF 排序位置随时间变化

文件：`epf_rank_vs_time.png`

- 横轴：`time_ms`
- 纵轴：target edge 用户在候选集内的 `candidate_rank_epf`
- `1` 表示候选集内最先分 PRB
- 只画 `in_candidate_window = true` 的点
- 对比 `tail_append` 与 `business_aware_constrained_insert`

解释重点：

- 如果 target 已经进入候选窗口但 rank 仍靠后，说明它还没有被 PDB 项强烈推到前面；
- 如果 rank 随时间明显前移，说明 HOL/PDB 压力正在增强。

### 图 3：谱效项与 PDB 项随时间变化

文件：`dominance_terms_vs_time.png`

- 横轴：`time_ms`
- 纵轴：诊断项数值
- 每个策略分别画：
  - `spectral_term`
  - `hol_factor`
- 加垂直参考线：`HOL = PDB / 2` 对应的第一个决策点
- 可选加垂直参考线：`HOL = PDB` 对应的第一个决策点

解释重点：

- `hol_factor < 1` 时，PDB 项尚未明显放大；
- `hol_factor >= 1` 后，PDB 项开始主导排序权重变化；
- 若 target 长时间不在候选窗口，则即使 `hol_factor` 增长，也不一定能马上影响 PRB 分配。

### 图 4：阶段时间轴

文件：`dominance_timeline.png`

- 横轴：`time_ms`
- 纵轴：两行策略：
  - `tail_append`
  - `business_aware_constrained_insert`
- 每个时间段用颜色表示阶段：
  - `queue_limited`
  - `spectral_dominated`
  - `pdb_dominated`
  - `overdue_pdb_forced`

解释重点：

- 对比两种策略在 `queue_limited` 阶段停留多久；
- 对比两种策略是否更早进入 `pdb_dominated`；
- 判断 ours 的优势是来自更早进入候选窗口，还是来自进入候选窗口后的排序提升。

## 报告结构

`diagnostic_report.md` 包含以下章节：

1. `# Target Edge PDB Dominance Diagnostic`
2. `## 场景设置`
3. `## 判定口径`
4. `## 图形总览`
   - 引用四张 PNG 图
5. `## 策略对比摘要`
   - target 首次进入候选窗口时间
   - target 首次进入 EPF rank 1 的时间
   - 首次进入 `pdb_dominated` 的时间
   - `queue_limited` 持续决策点数量
   - `spectral_dominated` 持续决策点数量
   - `pdb_dominated` 持续决策点数量
6. `## 解释结论`
   - 哪段时间是队列位置主导
   - 哪段时间是谱效主导
   - 哪段时间是 PDB 主导
   - tail 与 ours 的主要差别在哪里

## 实现方向

### 1. 增加诊断采集对象

新增一个轻量诊断 collector，例如：

```text
src/scheduling_sim/diagnostics.py
```

它负责：

- 在每次 `finish_phase()` 排序前接收 users、queue、candidates、ranked、time、phase；
- 找到 `is_target = true` 的 edge packet 所属 UE；
- 计算并保存一条 decision trace row。

该 collector 默认不启用，避免影响现有仿真性能和报告输出。

### 2. 在 simulator 中挂接可选诊断 collector

`UlSimulator` 增加可选参数，例如：

```python
UlSimulator(config, users, metrics, diagnostic_collector=None)
```

当 collector 存在时，在 `finish_phase()` 内 `plan_phase()` 前记录诊断点。

### 3. 新增单独脚本

新增脚本：

```text
scripts/run_target_edge_pdb_dominance_diagnostic.py
```

脚本负责：

- 读取专用 config；
- 分别运行 `tail_append` 与 `business_aware_constrained_insert`；
- 合并两种策略的 trace rows；
- 写出 CSV、JSON、PNG、Markdown。

### 4. 新增专用配置

新增配置：

```text
configs/target_edge_pdb_dominance_diagnostic.json
```

配置固定为本轮范围中的典型 case。它不需要 sweep 多个包大小或 PDB，只需要包含两种策略列表。

## 风险与取舍

### 风险 1：`spectral_dominated` 与 `pdb_dominated` 是工程判别，不是严格因果证明

`hol_factor >= 1` 只是可解释的切换点。真实排序仍然由 `spectral_term * hol_factor` 共同决定。因此报告文案应写成“诊断标签”而不是“唯一因果”。

### 风险 2：target 未进入候选窗口时，PDB 权重无法直接影响分配

这正是本报告要强调的点。若 target 长时间处于 `queue_limited`，则讨论谱效主导或 PDB 主导都不完整，必须先说明 active queue 位置约束。

### 风险 3：新增绘图库依赖

引入 `matplotlib` 会增加本地运行环境依赖，但本轮目标是快速得到可读图形并提高诊断解释力，因此这笔成本是可接受的。图形输出先以工程诊断为目标，不追求论文级美化。

## 验证

实现后至少验证：

1. 新脚本能跑通并生成 `diagnostic_report.md`；
2. CSV/JSON 中同时包含 `tail_append` 与 `business_aware_constrained_insert` rows；
3. trace rows 包含 `queue_rank`、`candidate_rank_epf`、`spectral_term`、`hol_factor`、`dominance_label`；
4. 四张 PNG 文件都被生成并被 Markdown 引用；
5. `queue_limited` 只在 target 未进入候选窗口时出现；
6. `pdb_dominated` 只在 target 进入候选窗口且 `hol_factor >= 1` 时出现；
7. 现有 CLI smoke tests 不受影响。
