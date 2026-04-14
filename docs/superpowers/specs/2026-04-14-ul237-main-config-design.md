# UL237 Main Config Design

**Goal:** 引入一套新的“主配置”口径：上行每个 `U-slot` 使用 `237 PRB`，并把 MCS 输入从手写 `bits_per_prb` 改为外部谱效表，由代码统一换算。

## Why

当前默认配置把无线口径直接写成了小规模 `mcs_table` + `106 PRB/U-slot`。这让：

- 历史实验和新主配置难以并存
- `bits_per_prb` 的来源不透明
- 报告中很难解释“这个 MCS 表是不是贴近标准原始口径”

新的主配置需要满足两点：

- 旧实验配置和旧输出保持不变
- 新的主配置可明确说明：`237 PRB/U-slot` + 外部 MCS 谱效表是新的默认研究口径

## Scope

- 新增外部 MCS 文件格式，字段为 `sinr_db`、`mcs_index`、`spectral_efficiency`
- 配置解析支持从 `mcs_table_path` 加载该文件
- 运行时把谱效统一换算为 `bits_per_prb`
- 新增一套“主配置” sensitivity config，旧 config 不变

## Non-Goals

- 不修改旧实验输出目录
- 不删除或重命名现有 config
- 不在这次修改里重构无线环境模型的其它部分

## Design

### MCS Source of Truth

新增 `configs/mcs/nr_ul_main.json`，把 MCS 原始输入独立存储。配置文件只引用它，不再在每个 config 内重复粘贴整张表。

### Conversion Rule

代码在加载配置时把 `spectral_efficiency` 换算成 `bits_per_prb`。为保证实现简单、可解释，这次按 PRB 带宽与仿真 slot 时长做统一折算：

- `bits_per_prb = round(spectral_efficiency * 180000 Hz * slot_duration_ms / 1000)`

在当前默认 `1 ms` slot 下，这等价于：

- `bits_per_prb = round(spectral_efficiency * 180)`

也就是用 `1 PRB = 180 kHz` 的简化带宽模型，把谱效直接折算成“每个仿真 slot、每个 PRB 可发送的净 bit 数”。后续如果要引入更细的 RE 开销模型，再单独扩展。

### Backward Compatibility

- 现有内联 `mcs_table` + `bits_per_prb` 继续支持
- 现有测试和旧 config 不需要改动即可继续工作

### Main Config

新增 `configs/target_edge_sensitivity_report_main.json`：

- `resources.total_prb_per_u_slot = 237`
- `radio.environment.mcs_table_path = "mcs/nr_ul_main.json"`
- 其余参数沿用当前 sensitivity 默认研究场景

## Validation

- 配置加载测试：验证 `mcs_table_path` 可加载，且谱效会被换算为 `bits_per_prb`
- 回归测试：旧内联 `mcs_table` 仍可正常加载
- 手工检查：新主配置中 `total_prb_per_u_slot = 237`
