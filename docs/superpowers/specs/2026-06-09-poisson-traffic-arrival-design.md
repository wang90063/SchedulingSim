# Poisson Traffic Arrival Design

## Goal

把当前“中心用户周期小包 + 边缘用户按周期触发大包”的确定性业务模型，扩展为支持两类业务按泊松过程到达的新场景，同时保持旧配置和旧实验脚本可继续运行。

## Current Behavior

当前仓库里的业务到达逻辑有两个明显特征：

- 背景用户依赖 `period_slots`，按固定 slot 间隔产生一个包；
- `PDB` 用户依赖 `burst_cycle_interval`，按固定 cycle 间隔在指定时机产生一个包。

这套模型的问题是：

1. 到达过程是确定性的，不能表达“随机到达的小包业务”和“随机触发的大包业务”；
2. 到达逻辑写在 `simulator.py` 里，和 `DSUUU` 主循环耦合较深；
3. 到达只在受限时机发生，不能表达“任何时隙都可能有新包到来”的场景。

## Agreed Scenario Semantics

本轮设计采用以下已确认口径：

- 背景用户业务为即时通信类小包；
- 背景用户包大小固定为 `128 Byte`；
- `PDB` 业务为图像类大包；
- `PDB` 到达事件的基本单位是“一个完整大包”；
- 背景业务与 `PDB` 业务使用两个独立的到达率；
- 到达率按“整类用户总 `lambda`”配置，而不是逐用户单独配置；
- `D / S / U` 任意时隙都允许产生新包；
- 同一时隙里允许同一用户收到多个包；
- 老的确定性到达模型需要继续保留兼容能力。

## Proposed Approach

采用“独立到达生成模块”的方案，而不是继续把到达逻辑堆在 `simulator.py` 里。

### Why This Approach

- 比直接在 `simulator.py` 里硬改更清晰，后续扩展新的业务模型成本更低；
- 比重构成完整事件系统更小、更稳，适合这次只改业务到达口径的目标；
- 能把“采样到达”“分配到用户”“注入 `LC`”这三个动作隔离出来并单测。

## Config Design

### New Traffic Fields

`traffic.center` 与 `traffic.edge` 都新增两类字段：

- `arrival_model`
- `total_lambda_per_slot`

建议新配置长这样：

```json
{
  "traffic": {
    "center": {
      "count": 63,
      "packet_bits": 1024,
      "pdb_ms": null,
      "gbr_bps": 7000,
      "arrival_model": "poisson",
      "total_lambda_per_slot": 1.8
    },
    "edge": {
      "count": 1,
      "packet_bits": 400000,
      "pdb_ms": 400,
      "arrival_model": "poisson",
      "total_lambda_per_slot": 0.15
    }
  }
}
```

### Backward Compatibility

- 若 `arrival_model` 未配置，则默认继续走当前确定性模型；
- `period_slots` 和 `burst_cycle_interval` 暂不删除，仍作为旧模型字段保留；
- 旧实验配置和已有报告脚本不要求在本轮同步迁移。

## Arrival Generation Design

新增模块：

- `src/scheduling_sim/arrivals.py`

该模块负责：

1. 按 slot 和业务类别采样到达数量；
2. 把采样出的整包随机分配给对应类别用户；
3. 生成用于注入 `LC` 的到达事件。

### Category-Level Poisson Sampling

每个 slot 分别对两类业务独立采样：

- 背景业务采样 `Poisson(lambda_bg_total)`
- `PDB` 业务采样 `Poisson(lambda_pdb_total)`

两类采样相互独立，不共享随机流。

### Packet Granularity

- 背景业务一次到达事件生成一个 `128 Byte` 小包；
- `PDB` 业务一次到达事件生成一个完整大包；
- 如果某个 slot 上 `PDB` 采样结果为 `k`，表示该 slot 有 `k` 个独立大包到达事件；
- 这里的 `k` 不是“大包被切分成 `k` 份”。

### User Assignment

对每个类别在该 slot 上采样出的 `k` 个到达事件：

- 在该类用户池中均匀随机分配；
- 抽样允许重复；
- 因此同一用户在同一 slot 收到多个包是合法结果。

这比“每用户单独配一个 `lambda`”更好设置，也更符合当前实验配置习惯。

## Slot Visibility Semantics

“任何时隙都可到达”不能等价于“任何时隙都立即参与本时隙已做出的控制决策”，否则会出现时序穿越。

本轮采用以下可见性规则：

- `D` slot 结束时采样并注入 `D` 到达包；
- 这些 `D` 到达包可以参与同周期后续的 `S` 控制决策；
- `S` slot 结束时采样并注入 `S` 到达包；
- `S` 到达包从下一周期开始可见；
- 每个 `U` slot 结束时采样并注入 `U` 到达包；
- `U` 到达包也从下一周期开始可见。

### Rationale

- `D` 之后还有 `S` 控制阶段，允许 `D` 到达影响 `S`，能体现“控制与到达交织”的新场景；
- `S` 和 `U` 之后不再有本周期新的控制机会，所以新包不能参与已经完成的决策；
- 这样既满足任意时隙可到达，也不破坏当前 `DSUUU` 决策执行顺序。

## Code Boundaries

### `src/scheduling_sim/config.py`

- 为 `TrafficConfig` 增加 `arrival_model` 与 `total_lambda_per_slot`；
- 保持现有旧字段可加载；
- 为未配置 `arrival_model` 的旧配置保留默认行为。

### `src/scheduling_sim/models.py`

- 为 `TrafficProfile` 增加 `arrival_model` 与 `total_lambda_per_slot`；
- 不改 `packet_bits`、`pdb_ms`、`gbr_bps` 的现有含义。

### `src/scheduling_sim/scenario.py`

- 继续负责建用户与灌入 `TrafficProfile`；
- 不负责任何到达采样逻辑。

### `src/scheduling_sim/arrivals.py`

- 实现泊松采样；
- 实现同类用户池上的随机分配；
- 输出 slot 级到达事件；
- 保持逻辑可在单测里独立验证。

### `src/scheduling_sim/simulator.py`

- 把现有 `_inject_u_slot_arrivals()` 的确定性逻辑替换为“按 slot 调用到达生成器”；
- 把到达注入从“只关心 `U` slot”扩展为 `D / S / U` 都能触发；
- `poisson` 模型下不再强制 `_preload_initial_backlog()`；
- 旧确定性模型继续保留预塞初始包的行为。

## Testing Strategy

### `tests/test_config.py`

验证：

- 新字段能正确从配置文件加载；
- 旧配置缺少新字段时仍保持兼容；
- `arrival_model = "poisson"` 时 `TrafficConfig` 取值正确。

### `tests/test_arrivals.py`

新增独立测试，验证：

- 背景类和 `PDB` 类总 `lambda` 独立生效；
- 在固定随机种子下，采样结果和分配结果可复现；
- 同一用户同一 slot 可被分到多个包；
- `PDB` 到达始终是“1 次事件 = 1 个完整大包”。

### `tests/test_simulator.py`

验证：

- `poisson` 模型下默认不预塞初始包；
- `D` 到达能影响同周期 `S`，`S/U` 到达只能下周期生效；
- 新到达包的 `eligible` 语义不穿越已完成控制决策；
- 旧 deterministic 模型行为不被回归破坏。

## Risks

- 旧实现只有 cycle 级可见性概念，本轮需要把部分到达可见性细化到 slot 级，容易在边界上出错；
- 泊松模型会让短仿真窗口的波动更大，个别 case 的结果稳定性可能下降；
- 如果未来需要更复杂的业务相关性，这个设计仍然是独立到达事件模型，不包含会话级状态。

## Non-Goals

- 不在本轮引入完整事件系统；
- 不修改调度算法、排序策略或无线环境模型；
- 不要求所有旧配置立刻切换到 `poisson`；
- 不在本轮重新设计业务 KPI 口径；
- 不在本轮引入“逐用户单独 `lambda` 配置”。

## Validation Plan

本轮设计完成后，实施阶段至少需要验证：

1. 一个显式 `poisson` 配置能在 CLI 下跑通；
2. 背景业务包大小已切到 `128 Byte`；
3. `PDB` 到达事件不会拆分成多个分段包；
4. `D/S/U` 三类 slot 的到达生效时序与设计一致；
5. 旧 deterministic 配置至少有一组回归用例保持通过。
