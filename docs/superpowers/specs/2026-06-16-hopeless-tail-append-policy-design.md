# Hopeless Tail-Append Policy Design

## Goal

Add a minimal reinsertion-policy variant that reuses the current hopeless-detection logic but changes the final fallback:

- if a target packet can still meet `PDB`, keep using the existing safe-position search
- if no safe position exists, do **not** front-insert
- instead, fall back to `tail_append`

The purpose is narrow: test whether the current `high_cost` point can reduce center-side cost while preserving at least part of the `PDB` recovery seen with `hopeless_front_insert`.

## Problem

The current rho-first scan already identified a representative `high_cost` point:

- `background_user_count = 40`
- `pdb_user_count = 4`
- `target_rho_bg = 0.775`
- `target_rho_pdb = 0.549`
- `background_packet_kb = 2.0`
- `background_period_ms = 12.5`
- `pdb_ms = 20`
- `pdb_packet_kb = 3.0`

At this point:

- `tail_append` keeps center throughput relatively high, but almost all `PDB` packets miss deadline
- `hopeless_front_insert` recovers some `PDB` satisfaction, but center throughput drops sharply because hopeless packets are still forced to the front

That leaves one unresolved question: when the scheduler has already judged a packet hopeless, is the extra center-side damage mainly caused by the **front insertion itself**?

## Existing Behavior

Current reinsertion policies already cover most of the needed logic:

- `tail_append`
  - always append to queue tail
- `constrained_insert`
  - append to tail if tail is safe
  - otherwise insert at the latest safe position
  - if no safe position exists, insert near the candidate window
- `hopeless_front_insert`
  - append to tail if tail is safe
  - otherwise insert at the latest safe position
  - if no safe position exists, insert at queue head

What is missing is a variant with the same hopeless detection as `hopeless_front_insert`, but a different hopeless fallback.

## Chosen Direction

Add a new policy:

- `hopeless_tail_append`

Behavior:

1. compute whether the tail position is safe using the existing completion estimate
2. if safe, append to tail
3. otherwise search backward for the latest safe position
4. if one exists, insert there
5. if none exists, append to tail

This keeps the implementation local to the reinsertion layer and avoids changing ranking, planning, radio modeling, or load-ratio mapping.

## Alternatives Considered

### 1. Reuse `constrained_insert`

Reject.

`constrained_insert` does not answer the target question because its hopeless fallback is not `tail_append`; it inserts near the candidate window.

### 2. Reuse `business_aware_constrained_insert`

Reject.

In the current code path this is only an alias to `ConstrainedInsertPolicy`, so it has the same mismatch as above.

### 3. Compare only `tail_append` and `constrained_insert`

Reject.

That would not isolate the effect of removing the front-insert action from the current `hopeless_front_insert` design.

### 4. Add a dedicated `hopeless_tail_append` variant

Choose this.

It is the smallest change that isolates exactly one mechanism: what to do after the packet is already judged hopeless.

## Scope

This change covers:

- one new reinsertion-policy name
- simulator/CLI wiring so the policy can be selected like existing variants
- focused tests for the hopeless fallback behavior
- one focused experiment on the already-identified `high_cost` point

This change does **not** cover:

- a full rerun of the entire rho-first scan
- any change to `EPF` ranking
- any change to wireless realization-bank generation
- any change to load-ratio mapping policy

## Implementation Design

### Reinsertion Layer

Keep `ConstrainedInsertPolicy` as the owner of:

- deadline-guard handling
- completion-time estimate
- safe-position detection

The new policy should reuse that logic rather than reimplementing it.

The cleanest shape is:

- add `HopelessTailAppendPolicy(ConstrainedInsertPolicy)`
- mirror the `HopelessFrontInsertPolicy.apply(...)` flow
- replace only the final fallback from `queue.insert_at(0, ue)` to `queue.append_tail(ue)`

No other reinsertion semantics change.

### Simulator Selection

`UlSimulator` currently selects among:

- `tail_append`
- `target_only_constrained_insert`
- `hopeless_front_insert`
- default constrained behavior

Add one explicit branch for:

- `hopeless_tail_append`

so it instantiates the new policy class.

### CLI Surface

The CLI `run --reinsert-policy` choices should accept:

- `hopeless_tail_append`

This keeps single-run checks and any downstream experiment scripts aligned with the existing interface.

## Experiment Design

Run only the already-known `high_cost` point, with the same wireless-environment control as the finished rho-first experiment:

- same realization-bank construction rules
- same `repeat_count = 10`
- same paired comparison discipline across policies
- same supply-side parameters and traffic mapping

Policies to compare:

- `tail_append`
- `hopeless_front_insert`
- `hopeless_tail_append`

The focused experiment should reuse the existing systematic-analysis machinery where possible, but it does not need a full 60-point config.

## Evaluation Metrics

Primary readout:

- `edge_pdb_satisfaction_rate`
- `center_agg_rate_bps`

Supporting readout:

- `center_prb_share`
- `edge_prb_share`
- `pdb_violation_rate`
- `edge_backlog_bits`
- `target_edge_completion_delay_ms`
- `target_edge_queue_wait_ms`

## Success Criteria

The experiment is useful if it answers both questions clearly:

1. compared with `hopeless_front_insert`, does `hopeless_tail_append` improve center-side cost
2. compared with `tail_append`, does `hopeless_tail_append` retain any meaningful `PDB` gain

The policy is not required to dominate both baselines. This is a mechanism test, not a guaranteed product decision.

## Testing Strategy

Use TDD and add only targeted coverage:

- reinsertion test showing that when no safe position exists, `hopeless_tail_append` moves the user to queue tail
- simulator test showing `UlSimulator` recognizes `hopeless_tail_append`
- CLI test showing `--reinsert-policy hopeless_tail_append` is accepted

The focused experiment itself is verification of the design hypothesis, not a unit-test substitute.

## Risks

### 1. Low differentiation from `tail_append`

If the tested scene is hopeless almost all the time, the new policy may behave nearly the same as `tail_append`.

That is acceptable because it still answers the mechanism question.

### 2. Low differentiation from `hopeless_front_insert`

If most packets still find a safe interior position, the new fallback may rarely trigger.

That is also acceptable; it means the `high_cost` damage is not primarily driven by the hopeless fallback branch.

### 3. Misinterpreting the result as a global conclusion

This spec intentionally limits the first pass to one representative point.

Any broader claim would require a follow-up scan after the mechanism is understood.
