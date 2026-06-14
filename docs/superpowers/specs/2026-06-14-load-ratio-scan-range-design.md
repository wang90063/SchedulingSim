# Load-Ratio Scan Range Design

## Goal

Define the next systematic scan as a controlled business-load sweep that:

- keeps the wireless side fixed
- keeps the user-class composition fixed
- covers light, medium, and heavy load
- expresses the scan primarily in resource-demand ratios
- maps every ratio point back into runnable business parameters

This design is a range-finding pass. Its purpose is to identify where `hopeless_front_insert` can produce `PDB` benefit under the current wireless assumptions, not to exhaustively sweep every business-model degree of freedom.

## Fixed Supply Side

The wireless side remains fixed to the current systematic-analysis foundation:

- `1 ms` slot duration
- `DSUUU` TDD pattern
- `273` `PRB` per `U-slot`
- background users drawn from `medium + good`
- `PDB` users drawn from `poor`

No wireless parameter is a sweep dimension in this pass.

This keeps interpretation clean: changes in outcome should come from business pressure, not from changed geometry or changed radio conditions.

## Why Load Ratio Is the Primary Axis

Three approaches were considered:

1. raw business-parameter sweep only
2. load-ratio sweep only
3. load-ratio primary sweep with business-parameter back-mapping

Use **approach 3**.

Approach 1 is easy to run but hard to interpret. If packet size, period, and user count all move directly, it becomes unclear whether a gain or loss came from total pressure, class share, or packet shape.

Approach 2 is clean analytically but cannot be run directly because the simulator needs concrete business parameters.

Approach 3 preserves both advantages:

- design and interpretation happen in ratio space
- execution happens in business-parameter space

## Why `PDB` Packet Shape Must Remain a Secondary Axis

The scan should be organized primarily by resource-demand ratios, but it must not collapse all `PDB` business shapes into a single average-load number.

The current scheduler changes queue position, not cell capacity:

- `reinsert` changes where a user re-enters the active queue
- `planning` still allocates finite `PRB` budgets per `U-slot`
- a packet is only complete after its `remaining_bits` reach zero

Because of that, two `PDB` traffic settings with the same average offered load can still interact differently with the scheduler:

- smaller packets can often be rescued by one earlier service opportunity
- larger packets may still need multiple `U-slots` after being moved forward
- shorter `PDB` values leave less slack even when average load is unchanged

Therefore the scan uses:

- load ratio as the **primary axis**
- `PDB` packet shape as a **small secondary axis**

The first pass must keep the packet-shape axis deliberately small so the matrix stays interpretable.

## Ratio Definitions

Let:

- `L_bg` = background offered load in `Mbps`
- `L_pdb` = `PDB` offered load in `Mbps`
- `C_bg` = background-class service capability in `Mbps`
- `C_pdb` = `PDB`-class service capability in `Mbps`

Define:

- `rho_bg = L_bg / C_bg`
- `rho_pdb = L_pdb / C_pdb`

For reporting the class resource mix, use:

- `prb_share_pdb = rho_pdb / (rho_bg + rho_pdb)`

This is more useful here than a raw throughput share because the background and `PDB` classes have very different `bits_per_prb`. The scan cares about how much of the effective `PRB` demand comes from `PDB`, not just how many `Mbps` it injects.

For `PDB` packet shape, define:

- `g_pdb = packet_bits / pdb_ms`

with units equivalent to per-user `Mbps`.

`g_pdb` is not swept independently. It is reported as a derived descriptor of each chosen `PDB` packet-shape point.

## Service-Capability Calibration

This scan uses the current controlled realization-bank calibration rather than a theoretical best-case peak.

Using the current `good + medium` background pool and `poor` `PDB` pool, the approximate class-average `bits_per_prb` values are:

- background mixed average: `403.12 bits/PRB`
- `PDB poor` average: `53.38 bits/PRB`

With `273 PRB/U-slot` and `600 U-slots/s`, the approximate class service capabilities are:

- `C_bg ≈ 66.03 Mbps`
- `C_pdb ≈ 8.74 Mbps`

These values are only used to define the first scan range and to label scene points. They are not substitutes for the simulator outputs.

## Business-Parameter Mapping

For periodic traffic:

- `L_bg(Mbps) = N_bg × bg_packet_kB × 8 / bg_period_ms`
- `L_pdb(Mbps) = N_pdb × pdb_packet_kB × 8 / pdb_ms`

So the ratio mapping is:

- `rho_bg ≈ N_bg × bg_packet_kB × 8 / (bg_period_ms × 66.03)`
- `rho_pdb ≈ N_pdb × pdb_packet_kB × 8 / (pdb_ms × 8.74)`

For the first pass, keep:

- `N_bg = 40`
- `bg_period_ms = 10`
- `N_pdb = 4`

and use packet size as the load knob.

This keeps the first range-finding pass simple:

- background pressure changes without changing background population structure
- `PDB` pressure changes without changing `PDB` population structure
- `PDB` packet shape remains explicit

## First-Pass Scan Matrix

### Background Axis

Use:

- `N_bg = 40`
- `bg_period_ms = 10`
- `bg_packet_kB ∈ {0.8, 1.2, 1.6, 2.0}`

This gives approximate background ratio points:

- `rho_bg ≈ 0.388`
- `rho_bg ≈ 0.582`
- `rho_bg ≈ 0.775`
- `rho_bg ≈ 0.969`

These cover light-to-heavy background pressure without pushing the first pass deep into obviously overloaded background-only territory.

### `PDB` Axis

Use:

- `N_pdb = 4`
- `PDB` packet shapes:
  - `100 ms`
  - `300 ms`
  - `500 ms`
- per-user `g_pdb` levels:
  - `0.4 Mbps`
  - `0.8 Mbps`
  - `1.2 Mbps`

Mapped packet sizes:

- `100 ms`: `5 / 10 / 15 KB`
- `300 ms`: `15 / 30 / 45 KB`
- `500 ms`: `25 / 50 / 75 KB`

This yields approximate `rho_pdb` points:

- `0.183`
- `0.366`
- `0.549`

The same `rho_pdb` values appear across multiple `PDB` packet shapes so the experiment can separate ratio effects from packet-shape effects.

### Total Scene Count

The first pass uses:

- `4` background points
- `3` `PDB` packet-shape groups
- `3` `PDB` intensity levels

Total scene points:

- `4 × 3 × 3 = 36`

This is intentionally smaller than the previous `81`-point grid because this pass is for finding the profitable region in a more principled coordinate system.

## Concrete Scene Table

| case | N_bg | bg_packet_kB | bg_period_ms | N_pdb | pdb_packet_kB | pdb_ms | rho_bg | rho_pdb | prb_share_pdb | g_pdb |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L01 | 40 | 0.8 | 10 | 4 | 5.0 | 100 | 0.388 | 0.183 | 0.321 | 0.4 |
| L02 | 40 | 0.8 | 10 | 4 | 10.0 | 100 | 0.388 | 0.366 | 0.486 | 0.8 |
| L03 | 40 | 0.8 | 10 | 4 | 15.0 | 100 | 0.388 | 0.549 | 0.586 | 1.2 |
| L04 | 40 | 0.8 | 10 | 4 | 15.0 | 300 | 0.388 | 0.183 | 0.321 | 0.4 |
| L05 | 40 | 0.8 | 10 | 4 | 30.0 | 300 | 0.388 | 0.366 | 0.486 | 0.8 |
| L06 | 40 | 0.8 | 10 | 4 | 45.0 | 300 | 0.388 | 0.549 | 0.586 | 1.2 |
| L07 | 40 | 0.8 | 10 | 4 | 25.0 | 500 | 0.388 | 0.183 | 0.321 | 0.4 |
| L08 | 40 | 0.8 | 10 | 4 | 50.0 | 500 | 0.388 | 0.366 | 0.486 | 0.8 |
| L09 | 40 | 0.8 | 10 | 4 | 75.0 | 500 | 0.388 | 0.549 | 0.586 | 1.2 |
| L10 | 40 | 1.2 | 10 | 4 | 5.0 | 100 | 0.582 | 0.183 | 0.239 | 0.4 |
| L11 | 40 | 1.2 | 10 | 4 | 10.0 | 100 | 0.582 | 0.366 | 0.386 | 0.8 |
| L12 | 40 | 1.2 | 10 | 4 | 15.0 | 100 | 0.582 | 0.549 | 0.486 | 1.2 |
| L13 | 40 | 1.2 | 10 | 4 | 15.0 | 300 | 0.582 | 0.183 | 0.239 | 0.4 |
| L14 | 40 | 1.2 | 10 | 4 | 30.0 | 300 | 0.582 | 0.366 | 0.386 | 0.8 |
| L15 | 40 | 1.2 | 10 | 4 | 45.0 | 300 | 0.582 | 0.549 | 0.486 | 1.2 |
| L16 | 40 | 1.2 | 10 | 4 | 25.0 | 500 | 0.582 | 0.183 | 0.239 | 0.4 |
| L17 | 40 | 1.2 | 10 | 4 | 50.0 | 500 | 0.582 | 0.366 | 0.386 | 0.8 |
| L18 | 40 | 1.2 | 10 | 4 | 75.0 | 500 | 0.582 | 0.549 | 0.486 | 1.2 |
| L19 | 40 | 1.6 | 10 | 4 | 5.0 | 100 | 0.775 | 0.183 | 0.191 | 0.4 |
| L20 | 40 | 1.6 | 10 | 4 | 10.0 | 100 | 0.775 | 0.366 | 0.321 | 0.8 |
| L21 | 40 | 1.6 | 10 | 4 | 15.0 | 100 | 0.775 | 0.549 | 0.415 | 1.2 |
| L22 | 40 | 1.6 | 10 | 4 | 15.0 | 300 | 0.775 | 0.183 | 0.191 | 0.4 |
| L23 | 40 | 1.6 | 10 | 4 | 30.0 | 300 | 0.775 | 0.366 | 0.321 | 0.8 |
| L24 | 40 | 1.6 | 10 | 4 | 45.0 | 300 | 0.775 | 0.549 | 0.415 | 1.2 |
| L25 | 40 | 1.6 | 10 | 4 | 25.0 | 500 | 0.775 | 0.183 | 0.191 | 0.4 |
| L26 | 40 | 1.6 | 10 | 4 | 50.0 | 500 | 0.775 | 0.366 | 0.321 | 0.8 |
| L27 | 40 | 1.6 | 10 | 4 | 75.0 | 500 | 0.775 | 0.549 | 0.415 | 1.2 |
| L28 | 40 | 2.0 | 10 | 4 | 5.0 | 100 | 0.969 | 0.183 | 0.159 | 0.4 |
| L29 | 40 | 2.0 | 10 | 4 | 10.0 | 100 | 0.969 | 0.366 | 0.274 | 0.8 |
| L30 | 40 | 2.0 | 10 | 4 | 15.0 | 100 | 0.969 | 0.549 | 0.362 | 1.2 |
| L31 | 40 | 2.0 | 10 | 4 | 15.0 | 300 | 0.969 | 0.183 | 0.159 | 0.4 |
| L32 | 40 | 2.0 | 10 | 4 | 30.0 | 300 | 0.969 | 0.366 | 0.274 | 0.8 |
| L33 | 40 | 2.0 | 10 | 4 | 45.0 | 300 | 0.969 | 0.549 | 0.362 | 1.2 |
| L34 | 40 | 2.0 | 10 | 4 | 25.0 | 500 | 0.969 | 0.183 | 0.159 | 0.4 |
| L35 | 40 | 2.0 | 10 | 4 | 50.0 | 500 | 0.969 | 0.366 | 0.274 | 0.8 |
| L36 | 40 | 2.0 | 10 | 4 | 75.0 | 500 | 0.969 | 0.549 | 0.362 | 1.2 |

## Expected Interpretation Value

This grid should answer four concrete questions:

1. At what background-pressure range does `proposed` first show measurable `PDB` gain?
2. As `PDB` demand increases, does the gain appear only in moderate `prb_share_pdb` or also in high-share regimes?
3. For the same `rho_pdb`, which `PDB` packet shapes are easier to rescue?
4. Where does the system cross from recoverable congestion into clearly hopeless overload?

The scan is considered successful if it narrows the profitable region enough to support a second, denser follow-up sweep around the transition band.

## Out of Scope for This Pass

This pass does not yet sweep:

- background user count
- `PDB` user count
- wireless parameters
- non-periodic background burstiness

Those dimensions can be reintroduced later after the profitable ratio region is located.
