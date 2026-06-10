# Periodic PDB Arrival With Fixed Analysis Window Design

## Background

Current `PDB` experiments in this repo are dominated by a single-burst model:

- edge users preload one large `PDB` packet at the beginning of the run;
- some reports stop when a target edge packet or the last selected edge packet finishes;
- `PRB` and satisfaction metrics are therefore tied to a completion-triggered window.

This model is useful for one-shot stress tests, but it does not represent a periodic `PDB` service. The requested scenario is different:

- each `PDB` user should keep sending large packets periodically;
- the period should be the user's own `pdb_ms`;
- the first packet should not be perfectly synchronized across all `PDB` users;
- metrics should be computed over a fixed large window, not a completion-triggered window.

## Problem Statement

We need a new simulation mode where `PDB` users behave like periodic large-packet sources instead of one-shot burst users.

The design must answer four concrete questions:

1. How should periodic `PDB` packet arrivals be generated?
2. How should the first-packet randomness be modeled?
3. How should a fixed analysis window be defined without corrupting satisfaction decisions for packets that arrive near the window end?
4. How should the new mode coexist with the existing single-burst experiments so old outputs and scripts do not break?

## Goals

- Add a periodic `PDB` arrival mode where each `PDB` user transmits once every `pdb_ms`.
- Add independent first-packet random phase for each `PDB` user with offset sampled from `[0, pdb_ms)`.
- Add fixed-window analysis, with the first version configured to `10s` by default.
- Keep old single-burst experiments reproducible and unchanged.
- Make the new scenario configurable rather than hardcoded, so the analysis window can be changed later without code redesign.

## Non-Goals

- Do not replace or reinterpret existing single-burst `PDB` experiments.
- Do not add per-cycle jitter after the first packet.
- Do not redesign the scheduler or queueing policy itself.
- Do not introduce a new reporting framework unrelated to this scenario.
- Do not redefine `center` background traffic generation in this work.

## Chosen Scenario Model

### Arrival Model

The chosen mode is:

- each edge `PDB` user sends one large packet every `pdb_ms`;
- `pdb_ms` is both:
  - the periodic arrival interval;
  - the packet deadline used for satisfaction checking.

This directly matches the requested semantics: "`PDB` 按照 `PDB` 的值进行发送".

### First-Packet Randomness

For each `PDB` user:

- sample `initial_offset_ms` independently from a uniform distribution on `[0, pdb_ms)`;
- the first packet arrival occurs at `initial_offset_ms`;
- subsequent arrivals occur at `initial_offset_ms + k * pdb_ms`, for integer `k >= 1`.

Only the first phase is randomized. There is no additional per-period jitter.

### Time Base

Periodic arrivals are defined in wall-clock milliseconds, not in reused `period_slots`.

Because the simulator serves traffic on slot boundaries, an arrival time that falls between scheduling boundaries is materialized at the next valid injection point in the simulator timeline. This keeps the scenario tied to real `ms` semantics while remaining compatible with the existing slot-based engine.

## Analysis Window Design

### Fixed Window

Add a configurable `analysis_window_ms`.

For the first version:

- default `analysis_window_ms = 10000`
- this corresponds to a fixed `10s` reporting window.

This parameter must remain configurable so later experiments can use a different large window without changing the implementation model.

### Which Packets Count In Satisfaction

A `PDB` packet belongs to the analysis window if:

- `arrival_time < analysis_window_ms`

Satisfaction is then defined over those packets only:

- denominator: all `PDB` packets whose arrival time is inside the analysis window;
- numerator: those packets whose completion satisfies `completion_time <= arrival_time + pdb_ms`.

This preserves the usual per-packet deadline semantics while moving the report to a fixed window.

### Why the Simulator Must Run Past 10s

If the simulator stops exactly at `10s`, packets that arrive near the end of the window may not have enough time to either complete or fail definitively.

Therefore, the simulator runtime for this mode should extend beyond the analysis window:

- runtime end should be at least `analysis_window_ms + max_pdb_ms`
- an optional small guard margin is acceptable if implementation convenience requires it

This extra tail is only for adjudicating packets that arrived inside the analysis window.

### Which Metrics Use Only the 10s Window

Load-type metrics must use only activity inside the fixed analysis window:

- `PRB` utilization
- `center` throughput
- `edge` throughput
- `system` throughput

The extra post-window runtime used for packet adjudication must not dilute these metrics.

This means the implementation should conceptually separate:

- `observation window`: `[0, analysis_window_ms)`
- `decision tail`: `(analysis_window_ms, analysis_window_ms + max_pdb_ms + guard]`

The observation window contributes to utilization and throughput metrics. The decision tail contributes only to satisfaction resolution for packets that already arrived before `analysis_window_ms`.

## Coexistence With Existing Modes

The new periodic scenario must coexist with current single-burst experiments rather than replacing them.

### Mode Split

Introduce an explicit arrival-mode distinction for edge `PDB` traffic:

- `single_burst`
- `periodic_by_pdb`

`single_burst` keeps current behavior unchanged.

`periodic_by_pdb` enables the new periodic large-packet model described in this spec.

### Why Explicit Mode Split Is Required

Without an explicit mode field, the same config fields would ambiguously mean different things across old and new experiments. That would make old result directories difficult to interpret and would increase the risk of silently changing historical experiment semantics.

An explicit mode preserves reproducibility and keeps reporting comparable.

## Configuration Design

The exact field placement can follow existing config style, but the design requires the following semantics.

### Required New Semantics

- edge arrival mode is configurable and defaults to legacy behavior unless explicitly changed;
- fixed analysis window is configurable and defaults to `10000 ms` for the new mode;
- first-packet phase randomization mode is configurable and defaults to uniform random phase.

### Recommended Config Shape

Recommended logical fields:

- `traffic.edge.arrival_mode`
  - `single_burst`
  - `periodic_by_pdb`
- `traffic.edge.initial_phase_mode`
  - `none`
  - `uniform_0_to_pdb`
- `simulation.analysis_window_ms`

The current `traffic.edge.pdb_ms` remains the per-user deadline value and becomes the periodic interval in `periodic_by_pdb`.

### Default Behavior

To avoid breaking old scenarios:

- existing configs without the new fields behave exactly as they do today;
- only configs that explicitly opt into `periodic_by_pdb` get the new arrival behavior;
- for opted-in configs, `analysis_window_ms` defaults to `10000` if omitted.

## Reporting Design

At minimum, periodic-window reports should retain or expose:

- `PDB` satisfaction rate
- `PRB` utilization
- `center` aggregate throughput
- `edge` aggregate throughput
- `system` aggregate throughput
- count of completed edge `PDB` packets
- count of in-window edge `PDB` packet arrivals

### Report Metadata

To avoid mixing old and new scenarios, outputs should also carry explicit metadata:

- `arrival_mode`
- `analysis_window_ms`
- `initial_phase_mode`

Output directory names and summary tables should reflect the mode, for example by including a periodic/fixed-window label.

## Implementation Boundaries

### Traffic Generation

Periodic `PDB` packet generation belongs in the traffic injection path, not in the reporting layer.

Responsibilities:

- determine per-user first-phase offset;
- generate periodic arrivals according to `pdb_ms`;
- inject packets at the next valid simulator scheduling point;
- stop generating new in-window packets once the analysis window is over.

### Metrics Layer

The metrics layer should distinguish:

- packets that arrived within the analysis window;
- resource usage that occurred within the analysis window;
- completions that happened during the decision tail for in-window packets.

This is the cleanest way to avoid mixing utilization and satisfaction semantics.

### Existing Single-Burst Paths

Existing behavior for:

- preloaded initial `PDB` packet,
- stop-when-target-finished logic,
- last-finished custom analyses,

should remain available and unchanged for legacy experiments.

## Error Handling And Edge Cases

### Edge Case: No PDB Users

If a scenario enables periodic mode but no users have `pdb_ms` set:

- periodic `PDB` arrival generation should produce no edge `PDB` packets;
- satisfaction denominator should be zero and reported consistently with current conventions.

### Edge Case: Window Shorter Than PDB

If `analysis_window_ms < pdb_ms`, the mode is still valid:

- some users may generate zero or one packet in-window depending on their random phase;
- satisfaction should still be judged packet-by-packet for whatever arrivals occur.

### Edge Case: Packet Arrives Near Window End

If a packet arrives just before `analysis_window_ms`:

- it is still counted in the satisfaction denominator;
- it may complete during the decision tail;
- its completion still counts toward satisfaction if the deadline is met.

### Edge Case: Legacy Configs

Configs that do not specify periodic mode must not accidentally switch behavior because of newly added defaults.

## Testing Strategy

At minimum, implementation should be covered by tests for:

1. legacy single-burst mode remains unchanged when new fields are absent;
2. `periodic_by_pdb` generates repeated edge arrivals at interval `pdb_ms`;
3. first-packet phase is deterministic under a fixed random seed and lies in `[0, pdb_ms)`;
4. packets arriving before `analysis_window_ms` are included in the satisfaction denominator;
5. packets arriving after `analysis_window_ms` are excluded from the denominator;
6. packets arriving near the end of the window can still be judged during the decision tail;
7. throughput and `PRB` utilization only count activity inside the fixed observation window;
8. report metadata clearly distinguishes `single_burst` from `periodic_by_pdb`.

## Alternatives Considered

### Alternative 1: Use a Single Global Period Parameter

Rejected because it breaks the requested semantic that each `PDB` user should send according to its own `pdb_ms`.

### Alternative 2: Randomize Every Period

Rejected because it adds timing jitter that was not requested and makes interpretation harder.

### Alternative 3: Keep Completion-Triggered Window

Rejected because the goal is explicitly a fixed large-window statistic rather than a packet-finish-triggered one.

## Final Design Summary

The approved design is:

- keep old `single_burst` behavior unchanged;
- add `periodic_by_pdb` as a new explicit edge arrival mode;
- in that mode, each `PDB` user sends one large packet every `pdb_ms`;
- first packet phase is independently sampled from `[0, pdb_ms)`;
- reporting uses a fixed configurable `analysis_window_ms`, with first version defaulting to `10s`;
- satisfaction is computed over packets arriving within the window;
- simulator runtime extends beyond the window to adjudicate those packets;
- utilization and throughput metrics count only activity inside the fixed observation window.
