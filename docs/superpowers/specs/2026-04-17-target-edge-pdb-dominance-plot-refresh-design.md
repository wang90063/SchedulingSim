# Target Edge PDB Dominance Plot Refresh Design

## 背景

现有 `target_edge_pdb_dominance_diagnostic` 已经能输出四张总览图，但在阅读上有两个痛点：

- `epf_rank_vs_time.png` 只能看全局趋势，前期 `0-100 ms` 的 rank 变化不够清楚。
- `dominance_terms_vs_time.png` 和 `dominance_timeline.png` 把 `tail_append` 与 `business_aware_constrained_insert` 叠在同一张图里，量级差异较大时不利于逐策略观察。

## 目标

在不破坏现有图和现有报告结构的前提下，增量补充更易读的新图：

- 保留现有四张原图，避免覆盖既有产物。
- 追加一张 `EPF rank` 前 `100 ms` 放大图。
- 追加两组按策略拆分的 `dominance terms` / `dominance timeline` 图。
- 在报告中新增“局部放大 / 分策略视图”小节，引用这些新图。

## 方案

采用增量方案 A：

1. 保留已有输出：
   - `queue_position_vs_time.png`
   - `epf_rank_vs_time.png`
   - `dominance_terms_vs_time.png`
   - `dominance_timeline.png`
2. 新增输出：
   - `epf_rank_vs_time_first_100ms.png`
   - `dominance_terms_tail_append.png`
   - `dominance_terms_business_aware_constrained_insert.png`
   - `dominance_timeline_tail_append.png`
   - `dominance_timeline_business_aware_constrained_insert.png`
3. 仅修改绘图脚本和 smoke test；诊断数据本身与判定口径不变。

## 影响范围

- 脚本：`scripts/run_target_edge_pdb_dominance_diagnostic.py`
- 测试：`tests/test_cli.py`
- 输出报告：`outputs/target_edge_pdb_dominance_diagnostic/diagnostic_report.md`

## 验证

- 运行目标 CLI smoke test，确认旧图仍存在、新图生成成功、报告包含新图引用。
- 不调整原始 trace、统计字段、判定标签与配置文件。
