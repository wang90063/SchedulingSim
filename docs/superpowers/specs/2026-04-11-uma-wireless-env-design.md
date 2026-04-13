# UMa 上行无线环境重构设计

## 1. 背景

当前平台已经具备 `DSUUU` 上行调度、`ePF` 排序、顺序 `PRB` 分配、尾插与受约束前插两种回插策略，以及基于 `SNR -> MCS -> bits_per_prb` 的简化无线环境。

现阶段无线环境仍有两个明显问题：

- `center` 与 `edge` 主要由静态标签和手工参数区分，缺少物理场景解释。
- `bits_per_prb` 目前主要依赖人工配置，难以稳定表达“小区中心/边缘、距离变化、链路质量变化”这些因素。

为了让“边缘用户大包、低谱效、跨多个时隙或周期发送”的核心研究问题更贴近真实链路，同时保持平台模块化与低耦合，需要把当前无线环境升级为“几何位置驱动的大尺度信道模型”。

## 2. 目标

本次设计只重构第一版无线环境，不改变平台整体定位。

目标如下：

- 采用 `UMa` 场景构建上行大尺度无线环境。
- 引入可配置的小区半径 `cell_radius_m`。
- 让 `center` 与 `edge` 用户通过距离段而不是纯标签来体现物理差异。
- 在保持当前调度接口不变的前提下，由无线环境输出更可信的 `SINR/MCS/bits_per_prb`。
- 修正边缘用户 `PRB cap` 的语义，使其成为“物理 `U slot` 级上限”。
- 增加 `center/edge` 分组指标，避免总指标掩盖边缘行为。

## 3. 不在本次范围内

本次设计明确不做以下内容：

- 不显式建模邻区干扰。
- 不引入逐 `RB` 快衰、多径、频域选择性。
- 不引入精细 `BLER/HARQ` 仿真。
- 不引入闭环功控、多天线层数、自适应 `rank`。
- 不修改“调度只在 `D/S` 上做，`U` 只执行”的时序语义。

## 4. 设计原则

- 几何驱动：链路质量优先由用户位置、路径损耗、阴影衰落等物理因素导出。
- 慢时变优先：第一版只保留大尺度与平稳 slot 级漂移，不追求链路级细节。
- 算法解耦：调度层只消费 `CurrentRadioState`，不感知路径损耗公式等无线实现细节。
- 参数可控：小区半径、距离段、干扰裕量、阴影衰落等都通过配置控制。
- 默认可解释：默认参数应明显拉开中心与边缘用户的链路差异。

## 5. 场景与参数

### 5.1 小区模型

第一版采用单小区 `UMa` 场景。

- `cell_radius_m`：可调，默认值 `500`
- 干扰建模：不显式建邻区，统一折算为固定 `interference_margin_db`
- 无线环境更新时点：只在 `D` 和 `S` 两个决策 `slot` 前刷新快照

### 5.2 用户距离段

用户的业务分组仍保留 `center` 与 `edge`，但无线质量不再直接由标签决定，而由距离段驱动。

默认距离段如下：

- `center_distance_range_m = [50, 150]`
- `edge_distance_range_m = [425, 500]`

设计意图：

- `center` 用户尽量靠内，形成更稳定、更高效的链路。
- `edge` 用户尽量贴近小区边缘，强化弱覆盖、大包长尾、跨多时隙发送的研究特征。

### 5.3 建议新增配置

无线环境配置建议新增以下字段：

- `scenario_type`: 第一版固定为 `uma`
- `cell_radius_m`
- `carrier_frequency_ghz`
- `noise_figure_db`
- `interference_margin_db`
- `shadow_std_db`
- `slow_fading_alpha`
- `slot_jitter_std_db`
- `center_distance_range_m`
- `edge_distance_range_m`
- `mcs_table`

其中：

- `mcs_table` 保留，因为调度层仍然需要通过它把 `SINR` 转成 `MCS` 与 `bits_per_prb`
- `bits_per_prb` 不再被视为“直接手工指定的主模型参数”，而是 `SINR/MCS` 计算链路的输出

第一版随仓库提供的 `configs/edge_compare.json` 默认采用以下取值：

- `scenario_type = "uma"`
- `cell_radius_m = 500`
- `center_distance_range_m = [50, 150]`
- `edge_distance_range_m = [425, 500]`
- `edge_per_u_slot_prb_cap = 18`

## 6. 无线环境数据流

### 6.1 静态数据

`ScenarioFactory` 在构建用户时，为每个用户固定以下无线侧静态属性：

- `user_class`
- `distance_to_bs_m`
- `edge_per_u_slot_prb_cap`（仅边缘用户）

这些静态信息进入 `RadioProfile`，作为无线环境长期状态的输入。

### 6.2 动态快照

无线环境在 `D` 和 `S` 决策前为每个用户生成 `CurrentRadioState`。

第一版计算链路如下：

1. 读取 `distance_to_bs_m`
2. 按 `UMa` 大尺度路径损耗模型计算路径损耗
3. 叠加阴影衰落
4. 叠加平稳慢时变抖动
5. 扣除噪声与固定干扰裕量，得到 `sinr_db`
6. 按 `mcs_table` 选择 `mcs_index`
7. 由 `mcs_index` 对应的 `bits_per_prb` 得到当前发送能力

输出字段如下：

- `sinr_db`
- `mcs_index`
- `bits_per_prb`
- `per_u_slot_prb_cap`

## 7. 与调度层的接口边界

调度层保持现有消费方式，不直接感知新的大尺度模型细节。

### 7.1 保持不变的接口

- `ranking` 仍然只读取当前瞬时速率和历史平均吞吐
- `planning` 仍然只读取当前 `bits_per_prb` 和 `per_u_slot_prb_cap`
- `reinsert` 仍然只读取本次规划后估算得到的 `service_bits_per_decision`
- `simulator` 仍然保持 `D/S` 决策、`U` 执行的时间语义

### 7.2 需要修正的点

当前边缘用户 `PRB cap` 的语义存在偏差：`D` 和 `S` 分开做规划时，`U2` 可能在同一个物理 `U slot` 上叠加两次 cap。

本次重构需要把 `PRB cap` 明确修正为：

- 边缘用户在单个物理 `U slot` 上最终生效的 `PRB` 总量上限
- 无论预算来自 `D` 还是 `S`，合并后都不能超过该上限

## 8. 指标与报表

本次重构后，报表除保留总指标外，还应补充分组指标：

- `center_completed_packets`
- `edge_completed_packets`
- `center_avg_delay_ms`
- `edge_avg_delay_ms`
- `center_pdb_violation_rate`
- `edge_pdb_violation_rate`
- `center_served_bits`
- `edge_served_bits`
- `center_completed_bits`
- `edge_completed_bits`

这样可以区分以下两种现象：

- 资源是否真的没有被发送出去
- 资源是否主要消耗在“仍未完整完成的大边缘包”上

## 9. 代码落点

### 9.1 配置层

`src/scheduling_sim/config.py`

- 增加 `UMa` 无线环境配置字段
- 保持当前配置加载方式，兼容必要的旧字段

### 9.2 核心模型层

`src/scheduling_sim/models.py`

- 在 `RadioProfile` 中增加 `distance_to_bs_m`
- 视需要补充 `sinr_db` 字段命名，统一当前无线快照语义

### 9.3 场景构建层

`src/scheduling_sim/scenario.py`

- 负责按 `center/edge` 距离段分配用户位置
- 保持 `1 UE = 1 LC` 不变

### 9.4 无线环境层

`src/scheduling_sim/wireless_env.py`

- 从“手工 `base_snr_db` 驱动”升级为“距离 + 路损 + 阴影衰落 + 慢时变”驱动
- 继续只输出调度层可消费的 `CurrentRadioState`

### 9.5 调度与仿真层

`src/scheduling_sim/planning.py`

- 修正物理 `U slot` 级 `PRB cap`

`src/scheduling_sim/simulator.py`

- 保持主循环时序不变
- 在执行 `U` 时保证合并后的边缘用户 `PRB` 不超过物理 `slot` 上限

### 9.6 指标与报表层

`src/scheduling_sim/metrics.py`

- 增加分组统计与 `served_bits/completed_bits` 统计

`src/scheduling_sim/reporting.py`

- 输出新的结构化汇总字段

## 10. 第一版验收标准

满足以下条件即可认为第一版无线环境升级完成：

- 同一份实验配置中，`center` 与 `edge` 用户因距离差异形成稳定链路分层
- 边缘用户在默认参数下明显更难完成大包发送
- `PRB cap` 在物理 `U slot` 级别严格生效
- 调度层无需理解路径损耗公式即可继续运行
- 平台能输出 `center/edge` 分组结果，支持解释边缘用户长尾行为

## 11. 风险与取舍

- 如果第一版直接追求精细 `BLER/HARQ`，会显著扩大实现范围，影响当前插队算法验证节奏
- 如果仍然以手工 `bits_per_prb` 为主，虽然实现简单，但物理解释性不足

因此本次设计明确取中间路线：

- 采用 `UMa` 大尺度模型提升真实性
- 保持慢时变和接口简洁，避免过度链路级化
- 先服务“边缘弱信道大包调度实验”这个核心目标
