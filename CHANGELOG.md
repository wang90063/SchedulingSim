# Changelog

All notable changes to this project are documented in this file.

## v0.1.0 - 2026-04-13

Initial milestone release for the uplink scheduling experiment platform.

### Added

- Layered uplink simulation flow for `D/S/U/U/U`, with `D` and `S` control-phase decisions and `U` slots only executing transmissions.
- Modular scenario construction for fixed center users and fixed edge users, including support for a single target edge UE plus background center UEs.
- Wireless environment modeling with configurable cell radius, user distance ranges, stable per-slot radio snapshots, and `SNR` to `MCS` to `bits_per_prb` mapping.
- Reinsert policy support for baseline tail insertion, constrained insertion, target-only constrained insertion, and business-aware constrained insertion.
- Edge-oriented planning controls, including edge-only `per_u_slot_prb_cap`, candidate-window planning, and merged `D/S` grants across the three `U` slots.
- Target-edge case-study and sensitivity report scripts:
  - `scripts/run_target_edge_pdb_sweep.py`
  - `scripts/run_target_edge_sensitivity_report.py`
- Config-driven experiment entry points for:
  - target-edge comparison
  - business-aware `PDB` sweep
  - sensitivity reports
  - center traffic `1600 bit/slot` variant

### Changed

- EPF ranking now uses slot-level instantaneous radio state together with historical average rate, and updates smoothly on a slot basis.
- Simulator metrics now expose target-edge completion delay, queue wait, service time, control-phase wait, inter-service time, served bits, and grouped business KPIs.
- CLI and config loading now support the richer radio-environment schema and the new experiment/report workflows.

### Notes

- Current scope is uplink only.
- The platform is optimized for studying large-packet edge-user behavior under constrained spectrum efficiency and bounded edge PRB allocation.
