# SchedulingSim

面向上行调度研究的实验平台，重点模拟**边缘用户大包、低谱效、受限 PRB、跨多个时隙完成传输**的场景，并支持把自研回插算法与基线算法放在同一套环境里做可重复对比。

当前版本：`v0.1.0`

## 这是什么

`SchedulingSim` 是一个聚焦上行链路的调度仿真平台，核心目标不是“做一个大而全的无线系统”，而是把你现在最关心的机制做成**可控、可替换、可扫参、可复现实验结果**的研究底座：

- 固定中心用户 + 固定边缘用户的场景建模
- `DSUUU` 时序下的控制决策与传输执行解耦
- 面向边缘大包的回插策略对比
- 细化到 `queue wait`、`service time`、`control-phase wait`、`inter-service gap` 的指标拆解
- 面向实验报告的配置化扫描与结果导出

如果你只想快速跑起来，看“基线 vs 我们算法”的差异，可以直接从“快速开始”看起。  
如果你更关心平台设计、无线环境抽象和算法落点，可以直接看“核心机制亮点”和末尾的设计文档链接。

## 平台关注的问题

这套平台当前主要解决下面这类问题：

- 一个边缘目标用户只有一个 `LC`，但包很大，例如 `40000 bit`
- 边缘用户谱效差、可分到的 `PRB` 有上限，需要多个 `U` slot 才能传完
- 调度决策不是每个 `U` 时隙单独做，而是在 `D` 和 `S` 控制相位做，再去驱动后续 `U/U/U`
- 希望比较“尾插基线”和“满足边缘时延目标的回插策略”在不同 `PDB`、用户数、`PRB cap` 下的行为差异
- 希望以后业务模型、无线环境、排序策略、回插算法都可以单独替换，而不是互相耦合

## 快速开始

### 环境要求

- `Python >= 3.12`
- 当前工程无第三方运行时依赖，直接用标准库即可运行

### 运行单次仿真

直接运行目标边缘用户对比场景：

```bash
PYTHONPATH=src python -m scheduling_sim.cli run configs/target_edge_compare.json
```

也可以在同一个配置上临时覆盖回插策略：

```bash
PYTHONPATH=src python -m scheduling_sim.cli run configs/target_edge_compare.json --reinsert-policy tail_append
PYTHONPATH=src python -m scheduling_sim.cli run configs/target_edge_compare.json --reinsert-policy target_only_constrained_insert
PYTHONPATH=src python -m scheduling_sim.cli run configs/target_edge_compare.json --reinsert-policy business_aware_constrained_insert
```

输出会写到配置文件指定的目录，例如：

- `outputs/target_edge_compare/report.json:1`

### 运行扫参与报告脚本

`PDB` 扫描：

```bash
PYTHONPATH=src python scripts/run_target_edge_pdb_sweep.py configs/target_edge_business_aware_pdb_sweep.json
```

灵敏度报告：

```bash
PYTHONPATH=src python scripts/run_target_edge_sensitivity_report.py configs/target_edge_sensitivity_report.json
```

高中心负载版本（中心业务 `1600 bit/slot`）：

```bash
PYTHONPATH=src python scripts/run_target_edge_sensitivity_report.py configs/target_edge_sensitivity_report_center1600.json
```

主实验 `400000 bit / PDB 500 ms` 版本：

```bash
PYTHONPATH=src python scripts/run_target_edge_sensitivity_report.py configs/target_edge_sensitivity_report_main_400k_pdb500.json
```

其中 `configs/target_edge_sensitivity_report_main_400k_pdb500.json` 里的 `simulation.deadline_guard_ms` 用来给受约束回插增加“预测完成安全裕量”：

- 默认值是 `0`，表示仍按 `completion_ms <= deadline_ms` 的贴边口径判断
- 当配置为正数时，安全判断会变成 `completion_ms <= deadline_ms - deadline_guard_ms`
- 这个配置适合用在临界实验上，避免出现 `499/503` 这种擦着 `PDB` 边界的结果
- 当前 `main_400k_pdb500` 实验默认使用 `deadline_guard_ms = 10`

运行后会在 `outputs/` 下生成结果，典型路径包括：

- `outputs/target_edge_pdb_sweep/pdb_sweep.json:1`
- `outputs/target_edge_sensitivity/sensitivity_report.md:1`
- `outputs/target_edge_sensitivity/sensitivity_rows.csv:1`
- `outputs/target_edge_sensitivity_center1600/sensitivity_report.md:1`
- `outputs/target_edge_sensitivity_main_400kbit_pdb500/sensitivity_report.md:1`

### 运行测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## 核心机制亮点

### 1. `DSUUU` 时序是平台的一等公民

平台不是把所有时隙都当成“同一种调度 slot”处理，而是明确区分：

- `D`：做一次控制决策
- `S`：再做一次控制决策
- `U/U/U`：只执行传输，不再重新做回插决策

当前实现对应的机制是：

- `D` 先基于当下快照计算候选集、排序和 `0 ~ 1.5N` 的资源规划
- 更新全局链表后，`S` 再基于新的队列状态计算 `1.5N ~ 3N` 的资源规划
- 后续三个 `U` slot 只按已经规划好的 `PRB` 去传 bit

这能把“控制决策造成的等待”和“真实 `U` 面上的传输/空等”清楚拆开。

### 2. 平台重点服务“边缘大包”问题

这不是一个平均吞吐导向的平台，而是专门为下面这类问题设计的：

- 边缘用户包大，单次发不完
- 边缘用户谱效差，`bits_per_prb` 低
- 边缘用户还有独立的 `per_u_slot_prb_cap`
- 因此一个包往往要多轮进入候选集、多次跨 `D/S/U` 周期才能真正完成

也正因为这样，平台会重点统计目标边缘包的：

- completion delay
- queue wait
- service time
- control-phase wait
- pre-first-service wait
- inter-service gap wait

### 3. 无线环境比“固定 bit/PRB”更细

当前无线环境支持更贴近实际的可调参数：

- `UMA` 风格小区半径
- 中心 / 边缘用户距离区间
- `SNR/SINR -> MCS -> bits_per_prb` 映射
- 慢衰落平滑项与逐 slot 抖动

这样，`EPF` 排序时看到的是**当前 slot 的瞬时速率**，而不是一个完全固定的静态速率。

### 4. 算法、环境、业务模型是松耦合的

平台设计时专门避免“改一个地方，别的地方全要跟着动”的问题。当前主要拆分为：

- 场景构造：负责生成中心/边缘用户与初始业务
- 无线环境：负责每个控制阶段前刷新当前无线状态
- 排序与规划：负责候选集、`EPF` 排序和 `PRB` 规划
- 回插策略：负责决定包在全局链表中的再进入位置
- 指标与报告：负责实验口径、指标聚合和结果落盘

因此后续如果你要：

- 换业务模型
- 加新的回插算法
- 换无线环境参数
- 扩展指标口径

都可以在相对独立的模块里改，不需要把整个平台一起重写。

## 当前支持的策略与实验

### 回插策略

CLI 当前支持以下策略：

- `tail_append`
- `constrained_insert`
- `target_only_constrained_insert`
- `business_aware_constrained_insert`

其中当前最值得关注的是两类：

- 基线：`tail_append`
- 我们的方法：`business_aware_constrained_insert`

### 典型实验场景

当前默认研究口径是：

- `1` 个目标边缘用户
- `63` 个中心背景用户
- 边缘目标大包 `40000 bit`
- 重点扫描：
  - 边缘 `PDB`
  - 边缘 `per_u_slot_prb_cap`
  - 中心用户数

### 结果指标

当前平台内置的结果口径包括：

- 全局指标
  - `avg_delay_ms`
  - `p95_delay_ms`
  - `p99_delay_ms`
  - `prb_utilization`
  - `served_bits`
- 中心用户口径
  - `center_avg_rate_bps`
  - `center_min_rate_bps`
- 边缘用户口径
  - `edge_avg_hol_ms`
  - `edge_p95_hol_ms`
  - `edge_backlog_bits`
- 目标边缘包口径
  - `target_edge_completion_delay_ms`
  - `target_edge_queue_wait_ms`
  - `target_edge_service_time_ms`
  - `target_edge_control_phase_wait_ms`
  - `target_edge_pre_first_service_wait_ms`
  - `target_edge_inter_service_gap_wait_ms`
  - `target_edge_time_to_first_service_ms`
  - `target_edge_pdb_met`
  - `target_edge_remaining_bits`

## 仓库结构

- `src/scheduling_sim/cli.py:1`
  - CLI 入口，负责加载配置、覆盖策略、运行仿真并输出报告
- `src/scheduling_sim/config.py:1`
  - 配置解析，包括仿真、流量、无线环境、调度与报告配置
- `src/scheduling_sim/scenario.py:1`
  - 场景工厂，负责构造中心/边缘用户、距离与初始业务
- `src/scheduling_sim/wireless_env.py:1`
  - 无线环境刷新与当前 slot 无线状态生成
- `src/scheduling_sim/ranking.py:1`
  - `EPF` 排序逻辑
- `src/scheduling_sim/planning.py:1`
  - 候选集、排序结果和 `PRB` 规划
- `src/scheduling_sim/reinsert.py:1`
  - 回插算法与队列再进入逻辑
- `src/scheduling_sim/simulator.py:1`
  - `DSUUU` 主循环与调度执行
- `src/scheduling_sim/metrics.py:1`
  - 指标收集、业务口径聚合和目标边缘包拆解
- `src/scheduling_sim/reporting.py:1`
  - 报告写出逻辑
- `configs/*.json`
  - 可直接运行的实验配置
- `scripts/*.py`
  - 面向扫参和报告生成的脚本
- `docs/superpowers/specs/*.md`
  - 设计文档与问题拆解

## 推荐阅读路径

如果你是第一次看这个仓库，建议按下面顺序：

1. 先跑 `configs/target_edge_compare.json`
2. 再看 `outputs/target_edge_compare/report.json:1`
3. 再跑 `configs/target_edge_sensitivity_report.json`
4. 再看 `outputs/target_edge_sensitivity/sensitivity_report.md:1`
5. 最后再去读设计文档，理解平台是怎么拆的

## 设计文档

如果你想继续扩展平台，而不是只跑现成实验，建议直接看这些文档：

- 总体设计：`docs/superpowers/specs/2026-04-09-ul-scheduling-sim-design.md:1`
- 无线环境设计：`docs/superpowers/specs/2026-04-11-uma-wireless-env-design.md:1`
- 平台模块结构：`docs/superpowers/specs/2026-04-13-platform-module-structure.md:1`
- Target edge case study：`docs/superpowers/specs/2026-04-13-target-edge-case-study.md:1`
- 业务指标报告设计：`docs/superpowers/specs/2026-04-13-business-kpi-report-design.md:1`

## 当前边界

当前版本有意保持简单，重点是把你的核心机制跑通，因此暂时不覆盖：

- 下行传输
- 多 `LC` / 多业务混合排队
- 更复杂的 `GBR/MBR/AMBR` 精细约束
- 完整系统级干扰协调

这些后续都可以在现有模块化结构上继续往里加。
