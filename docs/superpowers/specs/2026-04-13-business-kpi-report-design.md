# 业务目标 KPI 报表设计

## 背景

当前报表已经能输出总完成包时延、总 `throughput_bits`、`served_bits` 以及 `center/edge` 分组发送量。这个口径能解释“资源是否真的发出去了”，但不适合作为第一业务目标，因为边缘大包可能在仿真窗口内持续被发送却没有完成，此时总吞吐或完成包吞吐会低估边缘用户正在消耗的资源。

本阶段报表主口径改为双目标：

- 中心用户：看平均速率是否满足 `GBR`。
- 边缘用户：看完成包 `PDB` 满足情况，同时看未完成包 `HOL`，避免只统计完成包造成幸存者偏差。

## 目标

- 给中心用户流量配置增加 `gbr_bps`，默认 `0.0` 表示不启用门限。
- 按用户累计实际发送 bit，用整场仿真时间窗口计算用户平均速率。
- 输出中心用户 `GBR` 满足率和中心用户平均/最小速率。
- 输出边缘完成包 `PDB` 满足率、平均时延、P95 时延。
- 输出边缘未完成包 `HOL` 统计：平均 `HOL`、P95 `HOL`、超期 `HOL` 比例。
- 保留原有 `throughput_bits`、`served_bits`、`prb_utilization` 等字段作为诊断指标，不作为主目标。

## 非目标

- 不恢复 `minbr/gbr/mbr/ambr` 那套复杂业务模型。
- 不按滑动窗口统计 `GBR`，第一版只用整个仿真窗口。
- 不把中心用户 `PDB` 作为主目标，但继续保留整体和分组 delay 诊断。
- 不在本次重构 ranking、planning、reinsert 的插件注册机制。

## 业务口径

### 中心用户 GBR

`GBR` 是每个中心用户在整个实验窗口内的平均速率目标：

```text
user_avg_rate_bps = user_served_bits / simulation_duration_seconds
center_user_gbr_satisfaction_rate = 达到 gbr_bps 的中心用户数 / 中心用户总数
```

如果 `gbr_bps <= 0`，则认为中心用户没有配置 `GBR` 约束，满足率输出为 `1.0`，但仍输出中心用户平均速率和最小速率。

### 边缘用户完成包 delay

边缘完成包只统计 `user_class == "edge"` 且完成的包：

- `edge_pdb_satisfaction_rate = delay_ms <= pdb_ms 的边缘完成包数 / 边缘完成包总数`
- `edge_avg_delay_ms`
- `edge_p95_delay_ms`

如果没有边缘完成包，上述完成包型指标输出 `0.0`。

### 边缘用户未完成 HOL

仿真结束时，对所有边缘用户当前队头包做 `HOL` 快照：

- `edge_avg_hol_ms`
- `edge_p95_hol_ms`
- `edge_overdue_hol_ratio = HOL > PDB 的边缘队头包数 / 有未完成队头包的边缘用户数`

如果没有边缘未完成队头包，上述 `HOL` 指标输出 `0.0`。

## 数据流

1. `ScenarioFactory` 把 `traffic.center.gbr_bps` 写入中心用户 `TrafficProfile`。
2. `UlSimulator._consume_user_bits` 在每次实际发送 bit 时调用指标采集器，传入 `ue_id`、用户分组和发送 bit。
3. `UlSimulator.run` 在仿真结束前刷新最终 `HOL`，并把用户列表、仿真总时长传给 `MetricsCollector.build_summary`。
4. `MetricsCollector` 基于已完成包、按用户发送量、最终用户 `HOL` 快照生成业务 KPI 和诊断指标。
5. `reporting.write_report` 保持原样输出 JSON。

## 配置

`traffic.center` 支持新增字段：

```json
{
  "gbr_bps": 20000
}
```

`traffic.edge` 可以不配置 `gbr_bps`。第一版不对边缘用户做 `GBR` 目标。

## 测试策略

- 配置测试覆盖 `gbr_bps` 加载和默认值。
- 指标单元测试覆盖中心用户平均速率、`GBR` 满足率、边缘完成包 `PDB` 满足率、边缘最终 `HOL`。
- 仿真测试覆盖 `UlSimulator.run` 生成业务 KPI 字段。
- CLI smoke test 继续验证 `configs/edge_compare.json` 能生成包含业务 KPI 的 `report.json`。
