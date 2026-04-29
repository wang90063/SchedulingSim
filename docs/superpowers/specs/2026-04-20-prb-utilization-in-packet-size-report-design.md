# PRB 利用率指标接入设计

## 目标

在 `target_edge_packet_size_sensitivity` 报告中增加统一的系统级 `PRB utilization` 指标，帮助从 `PRB` 角度解释不同策略下的资源占用差异。

## 方案

- 直接复用 summary 中已有的 `prb_utilization`
- 在每张敏感性表格中增加两列：
  - `Baseline PRB Util`
  - `Ours PRB Util`
- 在报告“指标说明”中补充 `PRB Utilization = total_prb_used / total_prb_available`

## 口径

- 该指标按当前实验实际运行窗口统计
- 对于 `stop_when_target_edge_finished = true` 的配置，统计窗口会在目标边缘包完成时停止
- 因此跨策略比较时，需要结合完成时间一起解读，不把它误读为“系统凭空多出 PRB”
