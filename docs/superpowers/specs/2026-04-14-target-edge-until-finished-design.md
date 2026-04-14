# Target Edge Until Finished Design

## 背景

`configs/target_edge_sensitivity_report_main_400k_pdb500.json` 当前用 `cycles = 100` 和 `DSUUU`、`1 ms/slot` 形成固定 `500 ms` 仿真窗口。这个窗口来自实验配置，而不是目标边缘大包的真实完成时刻。对于 `400000 bit`、`PDB = 500 ms` 的目标包，固定窗口会让报告出现“窗口结束时还没发完”或依赖窗口长度的描述，不能回答“这个包最终发完用了多久”。

## 目标

把该实验改成“仿真到目标 edge 包发完为止”，并用真实运行到完成的时长更新报告和指标口径。这个能力应作为通用配置项实现，只在 `target_edge_sensitivity_main_400kbit_pdb500` 实验配置中启用，不把实验文件名或 `500 ms` 硬编码进模拟器。

## 非目标

- 不改变默认仿真行为；未启用新开关的配置继续按固定 `cycles` 窗口运行。
- 不改变调度策略、无线环境、PRB 规划或 MCS 表。
- 不用理论推算替代仿真；结果必须来自逐 slot 仿真推进后的目标包完成事件。
- 不修改无关实验配置。

## 设计

在 `simulation` 配置段增加一个可选停止条件字段，例如 `stop_when_target_edge_finished`，默认值为 `false`。配置加载器读取该字段；旧配置不包含该字段时行为不变。

`UlSimulator.run()` 继续按现有 `cycles` 上限推进，保留 `cycles` 作为安全上限，避免配置错误导致无限仿真。每个 U-slot 执行完、注入到达并刷新队列后，检查目标 edge 包是否已经完成。如果新开关启用且目标包已完成，就提前结束主循环。

实际仿真时长由停止时刻决定：

- 未提前停止：仍为 `cycles * len(tdd_pattern) * slot_duration_ms`。
- 提前停止：使用目标包完成所在 U-slot 的结束时刻作为 `simulation_duration_ms`。

报告脚本继续使用 summary 中的 `target_edge_completion_delay_ms`、`target_edge_queue_wait_ms` 和 `target_edge_service_time_ms`。启用新停止条件后，`target_edge_finished` 应为 `true`，报告不再依赖 `unfinished -> 499 ms` 或固定 `500 ms` 窗口语义。

## 数据流

1. `load_config()` 从 JSON 读取 `simulation.stop_when_target_edge_finished`，缺省为 `false`。
2. `ScenarioFactory` 和调度相关对象不需要变化。
3. `UlSimulator.run()` 在每个 U-slot 后检查目标包完成状态。
4. 完成时记录实际停止时长，并把该时长传给 `MetricsCollector.build_summary()`。
5. `run_target_edge_sensitivity_report.py` 使用新的 summary 结果生成 `target_edge_sensitivity_main_400kbit_pdb500` 报告。

## 测试计划

- 新增配置加载测试：缺省值为 `false`，显式设置为 `true` 可被读取。
- 新增模拟器行为测试：在一个目标 edge 包可快速完成的小场景中，启用该开关后，summary 的 `simulation_duration_ms` 小于固定窗口长度，并且 `target_edge_finished` 为 `true`。
- 更新 `tests/test_cli.py` 中 `target_edge_sensitivity_main_400k_report` 的断言，去掉对固定窗口未完成文案的依赖，改为验证报告包含“发完即停/真实完成时长”相关信息和差异列。

## 风险与约束

- `cycles` 仍是最大仿真上限。如果目标包在上限内仍无法完成，结果会保持现有未完成口径。
- 提前停止会改变中心用户平均速率的分母，因为 summary 中的 `simulation_duration_ms` 会变短。这是预期行为：该实验关注“目标包发完用了多长时间”，中心速率应按真实运行窗口计算。
- 如果未来需要“所有 edge 包都发完再停”或“某个 UE 发完再停”，可在相同停止条件框架下扩展，但本次只实现目标 edge 包完成即停。

## 自审

- 无占位符或待定项。
- 方案不硬编码实验名或 `500 ms`。
- 默认配置行为保持兼容。
- 测试覆盖配置读取、仿真停止和报告断言三层。
