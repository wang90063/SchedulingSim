# Edge Ratio Packet Sweep SINR 与统一 PDB 实验设计

## 背景

仓库里已经存在一批 edge-ratio packet-sweep 输出目录，例如：

- `outputs/edge_ratio_random_pdb_32users_packet_sweep_avg10_20260423_190938`
- `outputs/edge_ratio_random_pdb_48users_packet_sweep_avg10_20260423_182636`

这些结果已经能回答一部分问题：

- 固定总用户数下，随着扫描 edge 用户比例上升，`tail_append` 与 `business_aware_constrained_insert` 的 `PDB` 满足率如何变化；
- 当 edge 大包从 `10 KB` 增长到 `100 KB` 时，算法收益如何变化；
- 随机 `PDB` 混合场景下，中心背景吞吐与 `PDB` 用户满足率的 tradeoff 如何变化。

但当前这批结果有两个明显缺口：

1. 输出里没有正式保留用户无线条件，无法直接回答“这个场景里用户 `SINR` 分布到底是什么样”；
2. 这类实验没有稳定保留在 `scripts/` 下的正式入口，导致“扩包长到 `200 KB`”和“改成统一 `PDB = 200/400/600/800`”这类需求只能依赖历史目录或临时脚本，复现性差。

另外，从代码实现看，当前用户是静止用户：

- `distance_to_bs_m` 在建场景时一次采样并固定；
- `UMa` 阴影项按 `ue_id` 缓存并固定；
- 每个 slot 只在固定均值附近做小幅平滑抖动。

因此，对这个实验族来说，`SINR` 最值得观察的不是全量时序 trace，而是：

- 初始 / 稳定锚点 `SINR`；
- 每个用户在整个仿真窗口内的 `SINR mean/min/max`。

## 问题定义

本轮工作需要同时回答三类问题：

1. 对于现有结果目录 `outputs/edge_ratio_random_pdb_32users_packet_sweep_avg10_20260423_190938`，每一档扫描 edge 比例下，中心 / 边缘用户的初始 `SINR` 分布是什么；
2. 对于同类 edge-ratio packet-sweep 实验，如何把包长扫描从当前 `10, 30, 50, 70, 90, 100 KB` 扩到包含 `200 KB`；
3. 如何在保留现有随机 `PDB` 模式的同时，新增一套“所有扫描 edge 用户统一使用同一 `PDB` 档位”的正式实验模式，使 `200 / 400 / 600 / 800 ms` 四档可以稳定重跑和对比。

因此，本轮不是只补一张图或一份报表，而是要把这类实验提升为仓库内可重复执行的正式能力。

## 目标

- 为现有 `32 users` 历史输出目录生成一份可复查的 `SINR` 快照报告；
- 新增一个正式的 edge-ratio packet-sweep 实验脚本，替代“历史目录存在但仓库内无入口脚本”的状态；
- 在该正式脚本中保留现有随机 `PDB` 模式，并把包长扫描扩到 `200 KB`；
- 在该正式脚本中新增统一 `PDB` 模式，支持 `200 / 400 / 600 / 800 ms` 四档；
- 在逐用户结果里正式导出轻量无线统计字段，至少包含距离、初始 `SINR`、`SINR mean/min/max`。

## 非目标

- 不引入每个 slot 的全量 `SINR` trace 文件；
- 不修改现有 target-edge 主实验脚本的输出口径；
- 不新增第三种调度策略；
- 不在本次工作里重构整个 simulator 或 reporting 架构；
- 不回填历史目录里所有旧输出，只处理用户明确点名的 `32 users` 场景。

## 场景假设与无线口径

### 用户静止假设

当前 edge-ratio packet-sweep 实验按静止用户建模：

- `distance_to_bs_m` 由 `random_seed + index` 确定，一次采样后固定；
- `UMa` 阴影衰落项按 `ue_id` 固定；
- `refresh_slot()` 只在固定均值附近叠加平滑小扰动。

因此，本轮设计采用两层无线口径：

- **历史场景分析**：只输出“初始 / 稳定锚点 `SINR`”；
- **新正式实验输出**：输出逐用户 `initial_sinr_db` 与 `sinr_mean_db / sinr_min_db / sinr_max_db`。

### 参考无线环境

本实验族继续沿用现有主场景的 `UMa` 配置：

- `scenario_type = "uma"`
- `carrier_frequency_ghz = 3.5`
- `slot_duration_ms = 1`
- `slow_fading_alpha = 0.95`
- `slot_jitter_std_db = 0.5`

这些值不在本轮重新设计，只作为当前 edge-ratio packet-sweep 的标准背景口径继续使用。

## 输出一：历史 32 用户场景的 SINR 快照报告

### 输入

输入固定为现有目录：

- `outputs/edge_ratio_random_pdb_32users_packet_sweep_avg10_20260423_190938`

该目录已经包含：

- `experiment_manifest.json`
- `summary_report.md`
- `user_report.json/csv`
- `pdb_assignments.json`

但不包含用户级 `SINR` 字段。

### 设计原则

- 不重跑历史实验；
- 不依赖历史目录里是否保存过 `SINR`；
- 直接使用 `experiment_manifest.json` 与参考配置重建用户集合和无线环境；
- 对每个 ratio 档位只重建一次用户集合，因为同一 `requested_edge_ratio_pct` 下用户静态无线条件与 `repeat / policy / packet_kb` 无关。

### 输出文件

在原目录下新增：

- `sinr_snapshot_by_ratio.csv`
- `sinr_snapshot_by_ratio.json`
- `sinr_snapshot_report.md`

### `sinr_snapshot_by_ratio` 字段

每条用户记录至少包含：

- `requested_edge_ratio_pct`
- `actual_scanned_edge_ratio_pct`
- `scanned_edge_user_count`
- `total_users`
- `ue_id`
- `user_class`
- `distance_to_bs_m`
- `initial_sinr_db`
- `initial_mcs_index`
- `initial_bits_per_prb`

### `sinr_snapshot_report.md` 结构

报告建议包含：

1. 标题
2. 数据来源与恢复方法
3. 无线口径说明
4. 按 ratio 分节的中心 / 边缘用户 `SINR` 摘要
5. 总结性结论

每个 ratio 小节至少给出：

- 中心 / 边缘用户数量
- 中心 / 边缘用户 `SINR mean/min/max`
- 中心 / 边缘用户 `bits_per_prb mean/min/max`
- 若有必要，列出最差若干个 edge 用户的 `ue_id / distance / initial_sinr_db`

## 输出二：正式的 edge-ratio packet-sweep 实验脚本

### 新增脚本

新增正式入口：

- `scripts/run_edge_ratio_packet_sweep_report.py`

该脚本负责统一运行“固定总用户数、扫描 edge ratio、扫描 packet size、双策略、repeat 平均”的实验，并输出结构化报告。

### 为什么需要新脚本

当前仓库存在这类实验的历史输出，但 `scripts/` 下没有对应正式入口。这会带来三个问题：

- 用户无法直接复跑或改参数；
- 结果口径不受测试保护；
- 未来再加 `SINR` 字段、统一 `PDB` 模式或新增包长点时，容易再次落成一次性脚本。

因此，本轮应把这类实验补成正式、可复跑、可测试的仓库能力。

## 实验模式

正式脚本支持两种模式：

- `random_pdb`
- `uniform_pdb`

二者共用以下骨架：

- 固定 `total_users`
- 扫描 `requested_edge_ratio_pct`
- 扫描 `pdb_packet_kb`
- 对两种策略都运行：
  - `tail_append`
  - `business_aware_constrained_insert`
- 用相同 `repeat_index` 进行多次重复并汇总平均结果

### 模式一：`random_pdb`

沿用历史语义：

- 扫描 edge 用户从 `[null, 200, 400, 600, 800]` 中随机抽取 `PDB`
- `null` 视为非 `PDB` edge 用户
- 相同 `packet_kb / ratio / repeat` 下，两种策略复用同一份随机 `PDB` 分配

该模式需要在当前包长集合：

- `10, 30, 50, 70, 90, 100 KB`

基础上扩展为：

- `10, 30, 50, 70, 90, 100, 200 KB`

### 模式二：`uniform_pdb`

新增统一 `PDB` 语义：

- 所有被扫描的 edge 用户统一使用同一个 `PDB`
- `PDB` 扫描档位固定为：
  - `200`
  - `400`
  - `600`
  - `800`

该模式下：

- 不再给扫描 edge 用户分配 `null`
- 非 `PDB` 用户只保留中心背景用户
- `uniform_pdb_ms` 成为一级实验维度

### 关于“边缘用户的 PDB 限制是一样的”的解释

本设计将用户需求解释为：

- 在 `uniform_pdb` 模式下，同一轮实验中所有扫描 edge 用户都使用同一个 `PDB` 值；
- 需要对 `200 / 400 / 600 / 800 ms` 四个统一档位分别运行完整 sweep；
- 不混入 `null` 或其他随机 `PDB`。

## 包长扫描设计

### 随机 PDB 版

保留历史包长点并追加 `200 KB`：

- `10`
- `30`
- `50`
- `70`
- `90`
- `100`
- `200`

### 统一 PDB 版

默认沿用同一组包长点：

- `10`
- `30`
- `50`
- `70`
- `90`
- `100`
- `200`

这样两套实验可以直接横向比较，不需要额外对齐包长口径。

## 逐用户无线统计设计

### 需要新增的字段

在正式实验输出的逐用户结果中新增：

- `distance_to_bs_m`
- `initial_sinr_db`
- `sinr_mean_db`
- `sinr_min_db`
- `sinr_max_db`
- `initial_mcs_index`
- `initial_bits_per_prb`

如实现成本低，也可以补：

- `sinr_sample_count`

但不是必需项。

### 为什么不导出每 slot trace

不导出全量 trace 的原因：

- 当前用户是静止用户，逐 slot 波动只是小幅平滑扰动；
- 逐用户 `mean/min/max` 已足够支撑实验分析；
- 全量 trace 会显著放大 JSON / CSV 体积，且本轮没有明确分析需求。

## 实现结构

### 一、历史 SINR 快照渲染脚本

新增：

- `scripts/render_edge_ratio_sinr_snapshot.py`

职责：

- 读取历史输出目录的 `experiment_manifest.json`
- 恢复总用户数、ratio 扫描与参考配置
- 对每个 ratio 重建用户集合
- 调用无线环境 `reset()` 得到初始 `SINR`
- 写出 `sinr_snapshot_by_ratio.*` 与 Markdown 报告

它是一个只读分析工具，不负责重跑历史仿真。

### 二、正式 edge-ratio packet-sweep 脚本

新增：

- `scripts/run_edge_ratio_packet_sweep_report.py`

职责拆分为四层：

1. **case 生成**
   - 根据 `packet_kb / ratio / repeat / policy / pdb_mode` 生成单次仿真配置
2. **PDB 分配**
   - `random_pdb`：随机抽 `null/200/400/600/800`
   - `uniform_pdb`：所有扫描 edge 用户统一取 `200/400/600/800` 之一
3. **运行与采样**
   - 执行 simulator
   - 收集 summary
   - 收集逐用户结果
   - 合并无线统计
4. **报告落盘**
   - 写 manifest、summary、user report、per-repeat report 与 Markdown 报告

### 三、轻量无线统计采集

不建议把无线统计逻辑写死在报表脚本里，而是应在 simulator / metrics 附近新增轻量采集能力。

建议采集项：

- `initial_sinr_db`
- `sinr_sum`
- `sinr_count`
- `sinr_min_db`
- `sinr_max_db`

更新时机：

- `reset()` 后记录初始值
- 每次 `refresh_slot()` 后更新均值 / 极值统计

最终在逐用户结果中导出：

- `initial_sinr_db`
- `sinr_mean_db = sinr_sum / sinr_count`
- `sinr_min_db`
- `sinr_max_db`

### 四、输出文件结构

正式实验输出目录继续沿用当前风格，至少保留：

- `experiment_manifest.json`
- `pdb_assignments.json` 或 `pdb_configuration.json`
- `summary_policy_average.csv/json`
- `summary_gain_average.csv/json`
- `summary_policy_per_repeat.csv/json`
- `user_report.csv/json/md`
- `user_reports_by_repeat/*`
- `summary_report.md`

其中 `experiment_manifest.json` 至少新增以下元信息：

- `pdb_mode`
- `pdb_packet_kb_values`
- `uniform_pdb_ms_values`（仅统一 `PDB` 模式）
- `user_report_extra_columns` 中的无线字段说明

## 报告口径

### 历史 SINR 快照报告

目标是回答：

- 不同 edge 比例下，中心 / 边缘用户的静态无线分布差异有多大；
- 边缘用户是否普遍处于更差 `SINR` / 更低 `bits_per_prb` 区间；
- 某些极差 edge 用户是否足以解释大包传输中的明显尾部时延。

### 正式实验总结报告

新脚本的 `summary_report.md` 需要继续回答原有实验问题，并额外显式说明：

- 包长已扩展到 `200 KB`
- 当前运行模式是 `random_pdb` 还是 `uniform_pdb`
- 若为 `uniform_pdb`，本次汇总中的 `PDB` 档位如何组织

## 测试与验证

### 单元测试

需要新增测试覆盖以下行为：

- 无线统计采集：
  - `initial_sinr_db` 被正确记录
  - 多次 `refresh_slot()` 后 `sinr_mean/min/max` 正确更新
  - `distance_to_bs_m` 被带入逐用户输出
- case 生成与 `PDB` 分配：
  - `random_pdb` 模式下包长点包含 `200 KB`
  - `uniform_pdb` 模式下所有扫描 edge 用户 `PDB` 一致，且不出现 `null`
- 输出字段：
  - `user_report` 包含新增无线统计列
  - `experiment_manifest.json` 包含 `pdb_mode` 与新增扫描维度

### 脚本级测试

需要为两个脚本补 smoke test：

- `run_edge_ratio_packet_sweep_report.py`
  - 用极小实验矩阵跑一轮
  - 验证核心输出文件存在
- `render_edge_ratio_sinr_snapshot.py`
  - 指向现有 `32 users` 历史目录
  - 验证会生成 `sinr_snapshot_by_ratio.*` 与 Markdown 报告

### 手工验证

完成实现后，至少做以下手工检查：

1. 对 `outputs/edge_ratio_random_pdb_32users_packet_sweep_avg10_20260423_190938` 运行 `SINR` 快照脚本；
2. 检查边缘用户 `initial_sinr_db` 整体低于中心用户；
3. 运行新的 `random_pdb` 模式，确认 `summary_report.md` 中出现 `200 KB` 小节；
4. 运行新的 `uniform_pdb` 模式，确认结果中完整覆盖 `200/400/600/800` 四档，且 edge 用户不再混有随机 `null`。

## 风险与约束

### 1. 历史目录无法直接恢复逐 slot SINR

历史目录没有保存无线状态，因此只能恢复静态 `SINR` 快照，不能事后反推出整个历史 run 的 `SINR mean/min/max`。这不是缺陷，而是历史产物本身的信息边界。

### 2. 输出体积增长

逐用户结果新增无线统计列后，`user_report.json/csv` 会变大，但增长应远小于引入全量 slot trace。

### 3. 新脚本与旧目录命名对齐

为了避免用户混淆，新脚本的输出命名应清楚表达：

- 总用户数
- `pdb_mode`
- 是否 `avgN`
- 时间戳

例如：

- `outputs/edge_ratio_random_pdb_32users_packet_sweep_avg10_<timestamp>`
- `outputs/edge_ratio_uniform_pdb_32users_packet_sweep_avg10_<timestamp>`

## 推荐实现顺序

建议实现顺序如下：

1. 先补轻量无线统计采集与相关测试；
2. 再补历史 `SINR` 快照分析脚本；
3. 然后新增正式 edge-ratio packet-sweep 脚本并复现随机 `PDB` 版；
4. 最后在同一脚本中接入统一 `PDB` 模式、`200 KB` 扫描点与对应测试。

这样可以先把“看 `SINR`”这个用户当前最直接的问题解决，再逐步把实验入口正规化。
