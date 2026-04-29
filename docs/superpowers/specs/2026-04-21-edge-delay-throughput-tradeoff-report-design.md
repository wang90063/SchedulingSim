# 上行调度边缘时延-吞吐权衡实验报告设计

## 背景

当前结果目录 `outputs/center_pdb_null_rerun_prb273_20260421_000000` 已经包含：

- `target_edge_packet_size_sensitivity_400kb/sensitivity_rows.csv`
- `target_edge_packet_size_sensitivity_400kb/sensitivity_rows.json`
- `target_edge_packet_size_sensitivity_400kb/sensitivity_report.md`

这些结果已经覆盖 `400 KB` 目标边缘大包场景下的多维敏感度扫描，并提供了完整的底层统计字段。但现有 `Markdown` 更偏“原始实验记录”，还不够适合作为一次正式展示材料：图表组织不聚焦、指标公式不完整、系统结构说明不够集中，也没有单独把“边缘时延收益与整体吞吐代价的权衡”提炼成可展示结论。

本次工作要在不重新跑实验的前提下，直接基于现有结果组织出一份正式实验报告，用于解释以下问题：

1. 系统实现结构、关键实验参数与业务模型是什么；
2. 报告中所有核心指标如何定义、如何计算、分别意味着什么；
3. 当中心用户数增加、或中心单用户数据量增加时，两种算法的边缘时延、中心速率与 `PRB` 利用率如何变化；
4. 我们的算法是否在保障边缘用户时延的同时，尽量减小了对整体吞吐的影响。

## 目标

- 生成一份完整、正式、可直接展示的 `Markdown` 实验报告；
- 基于现有 `CSV / JSON` 自动绘制 `4` 张主图和 `1` 张补充权衡图；
- 报告正文同时适合技术报告阅读与汇报展示复述；
- 将“时延收益”与“吞吐代价”分离建模，避免只看单一吞吐指标得出片面结论。

## 非目标

- 不新增仿真场景，不修改现有实验配置；
- 不重新设计调度算法；
- 不引入新的实验维度，主报告只使用：
  - `center_user_count`
  - `center_packet_load_per_6_slots`
- 不将 `center_packet_granularity` 作为主图分析对象；
- 不替换现有 `target_edge_packet_size_sensitivity_400kb/sensitivity_report.md`，而是在上层输出新的正式报告。

## 数据来源与固定口径

### 输入文件

- `outputs/center_pdb_null_rerun_prb273_20260421_000000/target_edge_packet_size_sensitivity_400kb/sensitivity_rows.csv`
- `outputs/center_pdb_null_rerun_prb273_20260421_000000/target_edge_packet_size_sensitivity_400kb/config_rerun.json`

### 基础实验口径

- `TDD` 模式：`DSUUU`
- `slot_duration_ms = 1`
- `stop_when_target_edge_finished = true`
- `deadline_guard_ms = 10`
- 每个 `U-slot` 可用资源：`273 PRB`
- 候选调度用户上限：`max_ue_per_slot = 16`
- 默认中心背景业务：
  - `count = 63`
  - `period_slots = 6`
  - `packet_bits = 960`
  - `pdb_ms = null`
  - `gbr_bps = 7000`
- 默认目标边缘业务：
  - `count = 1`
  - `packet_bits = 3200000`（即 `400 KB`）
  - `pdb_ms = 500`
- 边缘单 `U-slot` 资源上限：`edge_per_u_slot_prb_cap = 273`

### 对比策略

- baseline：`tail_append`
- ours：`business_aware_constrained_insert`

### 主分析维度

- 用户数敏感度：`dimension = center_user_count`
- 中心用户数据量敏感度：`dimension = center_packet_load_per_6_slots`

### 锚点分析维度

为支撑“收益-代价权衡”章节，再额外使用 `edge_pdb_ms` 维度中的两个代表点：

- `PDB = 100 ms`
- `PDB = 500 ms`

## 正式输出物

### 报告文件

- `outputs/center_pdb_null_rerun_prb273_20260421_000000/uplink_scheduler_edge_delay_throughput_tradeoff_report.md`

### 主图文件

- `outputs/center_pdb_null_rerun_prb273_20260421_000000/user_count_sensitivity_edge_delay_breakdown.png`
- `outputs/center_pdb_null_rerun_prb273_20260421_000000/user_count_sensitivity_center_rate_prb_util.png`
- `outputs/center_pdb_null_rerun_prb273_20260421_000000/center_load_sensitivity_edge_delay_breakdown.png`
- `outputs/center_pdb_null_rerun_prb273_20260421_000000/center_load_sensitivity_center_rate_prb_util.png`

### 补充图文件

- `outputs/center_pdb_null_rerun_prb273_20260421_000000/latency_throughput_tradeoff_pdb_anchors.png`

## 报告结构

报告固定组织为以下 `6` 章：

1. 实验背景与目标
2. 系统实现结构、系统参数与业务模型
3. 指标定义与公式说明
4. 敏感度分析结果
5. 边缘时延收益与整体吞吐代价的权衡分析
6. 结论

### 第 1 章：实验背景与目标

说明问题背景、实验目的，以及为什么不能只看边缘时延，还必须同时看中心速率与系统吞吐。

### 第 2 章：系统实现结构、系统参数与业务模型

本章以“系统结构 + 参数表 + 业务模型”三段式组织：

- **系统实现结构**
  - 业务到达与队列积压
  - `ePF` 排序
  - 回插策略（队尾 vs 业务感知受约束前插）
  - `PRB` 分配
  - 指标统计
- **系统参数**
  - `TDD` 配比
  - `slot` 时长
  - `PRB` 总量
  - 调度候选上限
  - 无线环境关键参数
- **业务模型**
  - 中心背景用户：多用户、周期小包、`PDB = null`
  - 目标边缘用户：单用户、弱信道、大包、需要多个 `U-slot` 才能发完
  - 两种策略对目标用户的不同处理方式

这部分可配一张简化流程图或用分点文字描述，不要求新增复杂架构图。

### 第 3 章：指标定义与公式说明

本章必须完整覆盖正文、图表、结论中使用到的所有指标，并给出公式和变量含义。

#### 时延类指标

- `Completion Delay`
  - `T_completion = T_finish - T_arrival`
- `Queue Wait`
  - `T_queue = T_completion - T_service`
- `Service Time`
  - `T_service = N_service_slots × T_slot`
- `Control Phase Wait`
  - `T_control`
- `Pre-First-Service Wait`
  - `T_pre-first = T_first_service_start - T_arrival`
- `Inter-Service Gap Wait`
  - `T_gap`
- `Time to First Service`
  - `T_first = T_first_service_start - T_arrival`
- `PDB Met`
  - `1(T_completion ≤ PDB)`

并明确说明：

- `Queue Wait` 由控制阶段等待、首包前等待、片间等待等部分共同组成；
- 当前报告重点用 `Queue Wait` 与 `Service Time` 来解释完成时延变化来源。

#### 吞吐类指标

- `Center Avg Rate`
  - `R_center,avg = B_center / T_window`
- `Edge Aggregate Rate`
  - `R_edge,agg = B_edge / T_window`
- `Target Edge Rate`
  - `R_target = B_target / T_window`
- `System Aggregate Rate`
  - `R_sys = (B_center + B_edge) / T_window`
- `Analysis Window`
  - `T_window = target_edge_completion_delay_ms`

并明确说明：

- 当前所有吞吐统计统一在“目标边缘大包完成前”的窗口内进行；
- 因此跨策略比较吞吐指标时，需要结合完成时间一起解读。

#### PRB 利用类指标

- `Total PRB Utilization`
  - `U_total = PRB_used,total / PRB_available,total`
- `Center PRB Utilization`
  - `U_center = U_total × Share_center`
- `Edge PRB Utilization`
  - `U_edge = U_total × Share_edge`
- `PRB_available,total = N_u_slots × PRB_per_u_slot`

其中本实验中：

- `PRB_per_u_slot = 273`

#### 占比与效率类指标

- `Center PRB Share`
  - `Share_center = PRB_used,center / PRB_used,total`
- `Edge PRB Share`
  - `Share_edge = PRB_used,edge / PRB_used,total`
- `Center Bits per Used PRB`
  - `η_center = B_center / PRB_used,center`
- `Edge Bits per Used PRB`
  - `η_edge = B_edge / PRB_used,edge`

#### 报告中的派生指标

为支撑第 `5` 章权衡分析，补充定义以下派生量：

- `Latency Gain (%)`
  - `(Baseline Completion - Ours Completion) / Baseline Completion × 100%`
- `System Throughput Retention (%)`
  - `Ours System Agg Rate / Baseline System Agg Rate × 100%`
- `Center Throughput Retention (%)`
  - `Ours Center Avg Rate / Baseline Center Avg Rate × 100%`
- `Center PRB Util (%)`
  - `prb_utilization × center_prb_share × 100%`
- `Edge PRB Util (%)`
  - `prb_utilization × edge_prb_share × 100%`

### 第 4 章：敏感度分析结果

本章只展示 `4` 张主图，每组敏感度 `2` 张图，结构统一为：

- 先放图
- 再写“现象观察”
- 再写“机制解释”

#### 4.1 用户数敏感度

固定口径：

- `edge_pdb_ms = 500`
- 横坐标使用 `center_user_count`

##### 图 1：边缘时延拆解图

文件：

- `user_count_sensitivity_edge_delay_breakdown.png`

内容：

- 横轴：`center_user_count`
- 纵轴：时延（`ms`）
- 共 `6` 条线：
  - `Baseline Completion`
  - `Ours Completion`
  - `Baseline Queue Wait`
  - `Ours Queue Wait`
  - `Baseline Service Time`
  - `Ours Service Time`

设计要求：

- 颜色区分算法
- 线型区分指标类别
- 在 `31 / 63 / 79` 三档标出关键变化点

要表达的结论：

- 负载升高后，收益主要来自 `Queue Wait` 压缩，而不是 `Service Time` 大幅降低。

##### 图 2：中心速率 / PRB 利用率双纵轴图

文件：

- `user_count_sensitivity_center_rate_prb_util.png`

内容：

- 横轴：`center_user_count`
- 左纵轴：中心平均速率（建议以 `kbps` 展示）
- 右纵轴：`PRB utilization (%)`
- 左轴 `2` 条线：
  - `Baseline Center Avg Rate`
  - `Ours Center Avg Rate`
- 右轴 `6` 条线：
  - `Baseline Total PRB Util`
  - `Baseline Center PRB Util`
  - `Baseline Edge PRB Util`
  - `Ours Total PRB Util`
  - `Ours Center PRB Util`
  - `Ours Edge PRB Util`

要表达的结论：

- 我们的算法通过更早、更连续地服务目标边缘用户，提高了系统资源启用程度；
- 同时需要观察中心速率是否同步下降，以及下降是否只在高负载区显著出现。

#### 4.2 中心用户数据量敏感度

固定口径：

- `edge_pdb_ms = 500`
- 横坐标使用 `center_packet_load_per_6_slots`

##### 图 3：边缘时延拆解图

文件：

- `center_load_sensitivity_edge_delay_breakdown.png`

内容与图 `1` 相同，只是横轴变为：

- `中心单用户数据量（bit / 6 slots）`

要表达的结论：

- 中心单用户负载抬高后，baseline 的等待恶化更快；
- 我们的算法在拐点前仍能显著压缩边缘排队时延。

##### 图 4：中心速率 / PRB 利用率双纵轴图

文件：

- `center_load_sensitivity_center_rate_prb_util.png`

内容与图 `2` 相同，只是横轴改为：

- `center_packet_load_per_6_slots`

设计要求：

- 标注 `6400 bit / 6 slots` 作为接近饱和拐点；
- 解释拐点前后的系统行为差异。

### 第 5 章：边缘时延收益与整体吞吐代价的权衡分析

本章不重复敏感度主图，而是单独提炼“tradeoff”。

核心原则：

- **整体吞吐影响** 用 `System Aggregate Rate` 作为主指标；
- **背景业务代价** 用 `Center Avg Rate` 作为辅指标；
- 避免把“中心速率下降”等同于“整体系统吞吐下降”。

#### 锚点选择

采用以下三个代表点：

1. `PDB = 100 ms`
2. `PDB = 500 ms`
3. `center_packet_load_per_6_slots = 12000`

其中：

- `PDB = 100 ms` 表示强 deadline 压力下的激进边缘保护；
- `PDB = 500 ms` 表示默认主场景下更平衡的收益-代价点；
- `12000 bit / 6 slots` 表示系统接近饱和后的高负载校验点。

#### 论证链条

这一章固定按三层证据链写：

1. **强 deadline 情况下的资源重分配**
   - 用 `PDB = 100 ms` 说明算法会主动向目标边缘用户倾斜资源；
   - 强调此时中心速率可能下降，但系统总吞吐和 `PRB` 利用率未必下降。
2. **默认主场景下的平衡点**
   - 用 `PDB = 500 ms` 说明算法并不是一味牺牲背景业务；
   - 说明在较宽松 `PDB` 下，边缘时延仍显著改善，同时中心速率和系统吞吐可以保持稳定甚至提升。
3. **高负载饱和校验**
   - 用 `12000 bit / 6 slots` 说明整体吞吐代价主要发生在系统接近满载时；
   - 强调这是一种高占用条件下的边界现象，而不是算法在所有负载区间的普遍特征。

#### 补充图

文件：

- `latency_throughput_tradeoff_pdb_anchors.png`

建议内容：

- 横轴：`PDB = 100 ms`、`PDB = 500 ms`、`High Load = 12000 bit / 6 slots`
- 左轴：`Latency Gain (%)`
- 右轴：`System Throughput Retention (%)`
- 可在图注或正文补充 `Center Throughput Retention (%)`

要表达的结论：

- 我们的算法优先压缩边缘用户排队等待；
- 在中等负载或宽松 `PDB` 下，这种收益通常不需要以明显的整体吞吐下降为代价；
- 只有在系统接近满载时，整体吞吐保持率才开始出现可见损失。

### 第 6 章：结论

以 `3-5` 条结论收束，要求同时适合：

- 论文/报告正文引用
- 汇报场景直接口述

结论必须覆盖：

1. 收益主要来自 `Queue Wait` 下降；
2. 用户数和中心单用户负载上升时，baseline 更容易出现长等待放大；
3. 我们的算法会提高 `PRB` 利用率和边缘 `PRB` 占比；
4. 整体吞吐代价主要集中在高负载、近饱和区；
5. 默认主场景下算法实现了“边缘时延收益”与“整体吞吐影响控制”的平衡。

## 实现建议

建议新增一份专用报告生成脚本，直接读取现有 `sensitivity_rows.csv` 与 `config_rerun.json`，而不是重新调用仿真。

实现职责建议拆分为：

- 读取与筛选数据
- 派生指标计算
- 主图绘制
- 补充图绘制
- `Markdown` 报告渲染

报告中使用的所有数值结论都应直接来自现有结果文件，避免手工抄写。

## 验收标准

满足以下条件视为完成：

1. 指定路径下生成正式 `Markdown` 报告；
2. 指定路径下生成 `4` 张主图和 `1` 张补充图；
3. 报告包含系统结构、参数、业务模型、完整指标公式、敏感度分析、tradeoff 分析和结论；
4. 图表内容与现有 `CSV` 数据一致；
5. 报告正文能明确回答“是否在兼顾边缘时延的同时，尽量减少了对整体吞吐的影响”。
