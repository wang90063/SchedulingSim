# Target Edge 大包规模敏感性测试设计文档

## 背景

现有仓库已经有一套面向目标边缘大包的敏感性报告流程，典型输出为：

- `outputs/target_edge_sensitivity_main_400kbit_pdb500/sensitivity_report.md`

这套流程已经具备以下特征：

- 固定主场景配置后，对单一维度做 sweep
- 同时比较 `tail_append` 与 `business_aware_constrained_insert`
- 输出结构化 `CSV / JSON / Markdown`
- 在 Markdown 里提供较完整的场景说明、指标解释、表格对比、趋势分析

当前缺少的是另一类更贴近业务的问题：**当目标边缘包本身从中等大包扩展到超大包时，算法收益会如何变化**。相比只看单一 `400 KB` 场景，这次需要把“包大小”提升为一级观察维度，并继续扫描 `PDB` 与系统负载，形成一份按包大小分章节的完整报告。

## 问题定义

本次实验要回答的不是“某一个固定包大小下参数如何变化”，而是以下三类问题：

1. 当目标边缘包从 `400 KB` 增长到 `2 MB` 时，`tail_append` 与 `business_aware_constrained_insert` 的完成时延差值如何演化。
2. 在不同包大小下，`PDB` 收紧或放宽时，业务感知回插的收益是否会增强、减弱或出现平台区。
3. 在不同包大小下，背景中心用户数增加时，算法收益与中心吞吐代价是否同步放大。

因此，这次报告的主体应当是：

- **一级维度：包大小**
- **二级维度：`PDB` 扫描与中心用户数扫描**
- **对比轴：baseline vs ours**

## 目标

- 复用现有 target-edge sensitivity 报告框架，新增“按包大小分节”的扫描报告。
- 在 `400 KB / 800 KB / 1200 KB / 1600 KB / 2000 KB` 五档包大小下，分别执行：
  - `PDB` 扫描
  - 中心用户数扫描
- 保持现有 Markdown 报告风格，继续提供：
  - 场景说明
  - 指标说明
  - 分节表格
  - 趋势解读
  - 总结性结论
- 输出新的 `CSV / JSON / Markdown` 结果目录，便于后续继续画图和二次分析。

## 非目标

- 不在本次实验中新增第三种策略。
- 不在本次实验中重新设计调度算法。
- 不额外加入 `edge_per_u_slot_prb_cap` 扫描；本次只固定为“不限速”口径。
- 不将 no-PDB / EWMA 的新语义单独拆成另一份实验报告；若当前分支代码已经包含该能力，则本实验只使用其现状，不再单独评估算法版本差异。

## 固定场景口径

本次实验以当前主场景为基础，但对边缘 PRB cap 采用“无限制”口径。

### 无线与时隙口径

- TDD：`DSUUU`
- `slot_duration_ms = 1`
- 启用 `stop_when_target_edge_finished = true`
- 仍保留足够大的总周期上限，避免未完成场景无限运行

### 资源口径

- 每个 `U-slot` 的总资源固定为 `237 PRB`
- 边缘目标用户的 `edge_per_u_slot_prb_cap = 237`
- 这等价于边缘侧不再额外受 cap 限制，重点观察“调度顺序”而不是“边缘物理上限”

### 无线环境

- 继续沿用主场景 `UMa` 配置
- 小区半径、中心/边缘距离范围、MCS 表等参数维持现有主报告一致

### 调度与安全裕量

- baseline：`tail_append`
- ours：`business_aware_constrained_insert`
- `deadline_guard_ms = 10`

### 背景业务

- 默认中心用户背景包模型延续当前主场景
- 中心用户的小包大小、周期到达方式、无线口径维持现有主报告一致
- 除非处于“中心用户数扫描”小节，否则中心用户数默认固定为 `63`

## 扫描矩阵

### 1. 包大小一级维度

目标边缘包大小固定扫描以下五档：

- `400 KB`
- `800 KB`
- `1200 KB`
- `1600 KB`
- `2000 KB`

实现时需要统一换算为 bit 写入配置，避免 `KB / MB` 与 `bit / byte` 混淆。

推荐采用十进制换算，和现有报告风格保持一致：

- `1 KB = 1000 Byte`
- `1 Byte = 8 bit`

因此五档对应：

- `400 KB = 3,200,000 bit`
- `800 KB = 6,400,000 bit`
- `1200 KB = 9,600,000 bit`
- `1600 KB = 12,800,000 bit`
- `2000 KB = 16,000,000 bit`

### 2. 每个包大小下的 PDB 扫描

固定：

- `center_user_count = 63`
- `edge_per_u_slot_prb_cap = 237`

扫描：

- `edge_pdb_ms = 100 / 150 / 200 / 300 / 400 / 500`

### 3. 每个包大小下的中心用户数扫描

固定：

- `edge_pdb_ms = 500`
- `edge_per_u_slot_prb_cap = 237`

扫描：

- `center_user_count = 16 / 23 / 31 / 47 / 63 / 79`

### 4. 总实验规模

每个包大小包含：

- `6` 个 `PDB` 点
- `6` 个中心用户数点
- `2` 个策略

总计：

- `5 × (6 + 6) × 2 = 120` 次仿真

这个规模适合由单个批处理脚本串行完成，并输出统一汇总。

## 报告组织方式

本次采用“**按包大小分节**”的组织方案，而不是将所有维度混在同一批表里。

### 总体结构

报告结构建议为：

1. 报告标题
2. 场景设置
3. 对比策略
4. 调度机制说明
5. 指标说明
6. 按包大小分节的结果主体
7. 跨包大小趋势总结
8. 总结结论

### 包大小分节结构

对于每一个包大小，正文固定为：

#### `XX KB` 目标边缘大包场景

- 该节的局部说明
- `PDB` 扫描表
- `PDB` 趋势分析
- 中心用户数扫描表
- 中心用户数趋势分析
- 该包大小的小结

这样做的好处是：

- 读者可以先在单一包大小下理解规律
- 再在章节间横向比较 `400 KB -> 2 MB`
- 趋势解读更自然，不需要在一张超大表里来回跳转

## 指标与表格口径

Markdown 表格继续沿用当前 sensitivity report 的字段风格，至少保留：

- `Baseline Completion`
- `Ours Completion`
- `Baseline Queue Wait`
- `Ours Queue Wait`
- `Baseline Service`
- `Ours Service`
- `Baseline PDB`
- `Ours PDB`
- `Baseline Center Avg`
- `Ours Center Avg`
- `结论`

同时，汇总 `CSV / JSON` 继续保留底层拆分字段，至少包括：

- `target_edge_completion_delay_ms`
- `target_edge_queue_wait_ms`
- `target_edge_service_time_ms`
- `target_edge_control_phase_wait_ms`
- `target_edge_pre_first_service_wait_ms`
- `target_edge_inter_service_gap_wait_ms`
- `target_edge_time_to_first_service_ms`
- `target_edge_pdb_met`
- `target_edge_remaining_bits`
- `center_avg_rate_bps`

## 趋势解释要求

这次报告不能只给表，必须在 Markdown 正文里提供“包大小视角”的趋势解释。

### 1. 单个包大小内部趋势

对于每一个包大小，至少解释：

- `PDB` 从紧到松时，收益如何变化
- 中心用户数从低到高时，收益如何变化
- 目标包完成时延的变化主要来自：
  - `Queue Wait`
  - 还是 `Service Time`

### 2. 跨包大小趋势

报告后半段必须新增一段跨章节总结，回答以下问题：

- 包越大，`Completion Delay` 的绝对收益是否通常更大
- 包越大，收益占基线时延的相对比例是否也同步扩大
- 包越大时，`Inter-Service Gap Wait` 是否更容易成为主导收益来源
- 在边缘无 cap 条件下，中心平均吞吐的受损是否会随包大小增加而更明显

### 3. 机理解释口径

趋势分析时，建议统一使用以下解释框架：

- **大包跨更多 DSUUU 周期**：包越大，越容易暴露 baseline 队尾轮转带来的长空等
- **回插策略降低 inter-service gap**：我们的收益应主要体现为两次服务之间少空等
- **物理资源与排序收益分离**：本次边缘不再受 `24 PRB/U-slot` 这类硬 cap 限制，重点观察顺序优化本身带来的收益与代价
- **中心吞吐代价可见化**：由于边缘用户不受 cap 限制，大包连续吃资源的能力更强，因此需要特别观察中心平均吞吐是否被更明显压缩

### 4. 正文中的明确关注点

每个章节及总总结中，应优先回答：

1. 该包大小下我们的收益是否显著。
2. 收益主要来自等待时间压缩，还是服务时间变化。
3. 收益是否伴随更明显的中心吞吐损失。
4. 当 `PDB` 或负载上升时，收益是继续扩大，还是开始收敛。

## 实现设计

### 1. 输入配置

建议基于现有主场景配置新建一个专用实验配置，例如：

- `configs/target_edge_packet_size_sensitivity_main_uncapped.json`

该配置用于承载：

- 主场景固定口径
- sweep 维度列表
- 输出目录
- 策略列表

### 2. 脚本策略

建议不要新写一套完全独立的报告系统，而是在现有：

- `scripts/run_target_edge_sensitivity_report.py`

的基础上扩展，或者在其模式稳定的前提下新增一个同风格脚本，例如：

- `scripts/run_target_edge_packet_size_sensitivity_report.py`

推荐新增脚本而不是硬改旧脚本，以避免：

- 影响现有 `400kbit pdb500` 报告
- 让原脚本承担两种过于不同的章节组织逻辑

### 3. 数据组织

输出行数据应至少增加一个新维度字段，用于表达目标边缘包大小，例如：

- `edge_packet_bits`
- 或 `edge_packet_kb`

推荐两个都保留：

- 底层存 bit
- 报告渲染层按 `KB` 展示

### 4. 输出目录

建议新增专用输出目录，例如：

- `outputs/target_edge_packet_size_sensitivity_main_uncapped/`

目录下至少包含：

- `sensitivity_report.csv`
- `sensitivity_report.json`
- `sensitivity_report.md`

## 验证要求

需要覆盖三类验证：

### 1. 数据维度完整性

- 每个包大小都要同时存在：
  - `PDB` 扫描结果
  - 中心用户数扫描结果
- 每个参数点都要同时存在：
  - baseline
  - ours

### 2. 报告结构正确性

- Markdown 中应出现五个包大小章节
- 每个章节应出现两张主表：
  - `PDB` 扫描
  - 中心用户数扫描
- 场景说明中必须明确写出：
  - `edge_per_u_slot_prb_cap = 237`
  - 即边缘无额外 cap 限制

### 3. 趋势文本存在性

- 报告不能只有表格
- 需要出现：
  - 单节趋势分析
  - 跨包大小总结
- 趋势解读中要明确提到：
  - `Queue Wait`
  - `Service Time`
  - 中心吞吐影响

## 风险与权衡

### 1. 报告长度显著增加

按五个包大小分别写两类扫描，Markdown 会明显变长。这是预期行为，因为本次目标本来就是形成“可读的业务分析报告”，而不是只给一张总表。

### 2. 无 cap 口径下中心吞吐更敏感

因为边缘用户可以直接吃满更大资源，本次结果里中心平均吞吐的下降可能比旧报告更明显。正文需要把这点写清楚，避免把“边缘收益更大”误读成“纯策略优化无成本”。

### 3. 大包场景可能出现极大时延跨度

当包增长到 `2 MB` 且负载较高时，baseline 可能出现非常长的完成时延。报告需要用统一格式描述 finished / unfinished，避免表格和结论文字不一致。

## 推荐实施顺序

1. 新建专用实验配置，固定边缘无 cap 的主场景
2. 新建或扩展 sweep 脚本，加入 `edge_packet_size` 一级维度
3. 产出统一的 `CSV / JSON`
4. 基于结果渲染新的 Markdown 章节结构
5. 补充跨包大小趋势总结
6. 运行一次完整批实验并检查报告可读性

## 预期交付物

- 配置文件：
  - `configs/target_edge_packet_size_sensitivity_main_uncapped.json`
- 脚本：
  - `scripts/run_target_edge_packet_size_sensitivity_report.py`（推荐）
- 输出目录：
  - `outputs/target_edge_packet_size_sensitivity_main_uncapped/`
- 输出文件：
  - `sensitivity_report.csv`
  - `sensitivity_report.json`
  - `sensitivity_report.md`

## 一句话结论

这次实验的核心不是再做一份“单一参数 sweep”，而是把**目标边缘包大小**提升为一级观察维度，在边缘无 cap 条件下，系统性回答：**包越大时，业务感知回插的收益是否更大、收益来自哪里、以及它为中心业务带来的代价是否同步扩大。**
