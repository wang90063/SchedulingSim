# 目标边缘大包 Case Study 设计

## 目标

本实验不再先看多个边缘用户的群体平均指标，而是聚焦一个目标边缘用户的一个 `40000 bit` 大包。

核心问题：

> 在 63 个中心背景用户持续竞争时，目标边缘大包能否在中心 `GBR` 不明显变差的前提下更早传完？

## 用户与业务

- `63` 个中心背景用户，沿用当前中心周期业务模型。
- `1` 个目标边缘用户，实验开始时注入一个 `40000 bit` 大包。
- 目标边缘用户后续不再注入新包，避免多包干扰。

## 指标

目标边缘包指标：

- `target_edge_finished`
- `target_edge_completion_delay_ms`
- `target_edge_queue_wait_ms`
- `target_edge_service_time_ms`
- `target_edge_time_to_first_service_ms`
- `target_edge_served_bits`
- `target_edge_remaining_bits`

中心约束指标：

- `center_user_gbr_satisfaction_rate`
- `center_avg_rate_bps`

## 策略

- 基线：`tail_append`
- 我们的方法：`target_only_constrained_insert`

`target_only_constrained_insert` 只对带 `is_target = true` 的目标包执行受约束回插，其它中心背景用户仍然采用队尾插入。这样可以把目标边缘包的机制收益从“所有用户全局重排”里分离出来。

后续主口径合并为 `business_aware_constrained_insert`：所有 UE 走同一套受约束回插逻辑，但中心背景业务配置宽松 PDB，使其自然退化为队尾；目标边缘大包配置更紧 PDB，在预测队尾无法满足时才往前插。`target_only_constrained_insert` 保留为 debug/ablation 策略，不再作为主算法命名。

## 判优规则

优先满足：

1. 目标边缘包更早完成，或基线未完成而我们完成。
2. 中心 `GBR` 满足率相对下降不超过 `10%`。

辅助解释：

- 如果服务时间接近但等待时间下降，说明优势来自链表回插位置，而不是无线条件变化或 PRB cap 放水。
- `target_edge_queue_wait_ms` 当前定义为 `completion_delay_ms - service_time_ms`，包含 `D/S` 控制时隙和未服务的 `U` 时隙；如果要验证“纯链表排队等待是否被消除”，需要另加候选集进入时间/候选集外等待时间指标。
- PRB 分配需要按 HOL 包剩余 bit 截断，避免中心小包占满整个 U slot 后人为抬高目标边缘包等待。
- U slot 到达的包需要按 packet 记录 eligibility，不能只用 LC 级 `eligible_cycle`。否则新到达包会把已有旧 HOL 的整个 LC 标成下周期 eligible，导致中心用户被临时移出 active queue，进而让队尾基线过早轮转到目标边缘用户。

## 当前结果

修正 PRB 按包大小截断和 HOL packet eligibility 后，`configs/target_edge_compare.json` 的结果为：

| 指标 | `target_only_constrained_insert` | `tail_append` |
| --- | ---: | ---: |
| `target_edge_completion_delay_ms` | `119` | `188` |
| `target_edge_queue_wait_ms` | `81` | `151` |
| `target_edge_service_time_ms` | `38` | `37` |
| `target_edge_time_to_first_service_ms` | `8` | `8` |
| `target_edge_pdb_met` | `true` | `false` |
| `center_user_gbr_satisfaction_rate` | `1.0` | `1.0` |

这个结果符合 64 用户、每次 `D/S` 调度前 `16` 个候选时的队尾轮转直觉：`tail_append` 下目标边缘用户不会在两个连续调度周期持续被调度，而是在每轮队尾循环后才重新进入候选集；受约束回插在 PDB 压力下会把目标包提前放回候选窗口。

## 合并后的 PDB Sweep 结果

`configs/target_edge_business_aware_pdb_sweep.json` 将中心背景业务 `pdb_ms` 设为 `1000000000`，用来表达中心小包非时延敏感、自然回队尾；目标边缘大包扫描 `PDB = 100/150/200 ms`：

| Edge PDB | `tail_append` 完成时延 | `business_aware_constrained_insert` 完成时延 | 结论 |
| ---: | ---: | ---: | --- |
| `100 ms` | `179 ms` | `99 ms` | 我们的方法满足 PDB，基线超时 |
| `150 ms` | `179 ms` | `149 ms` | 我们的方法满足 PDB，基线超时 |
| `200 ms` | `179 ms` | `179 ms` | 基线已满足 PDB，我们的方法退化为队尾 |

完整结果见 `outputs/target_edge_pdb_sweep/pdb_sweep.md`。
