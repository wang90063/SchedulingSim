# UL237 Main Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为仿真新增 `237 PRB/U-slot` 的主配置，并支持从外部 MCS 谱效文件加载、换算 `bits_per_prb`。

**Architecture:** 保持现有 `mcs_table` 内联格式兼容，同时在 `config.py` 增加 `mcs_table_path` 读取分支。配置解析阶段把谱效统一换算为 `bits_per_prb`，无线环境和调度逻辑继续只消费 `bits_per_prb`，无需改动核心仿真流程。

**Tech Stack:** Python 3.12, `unittest`, JSON config files

---

### Task 1: Add config loader coverage

**Files:**
- Modify: `tests/test_config.py`
- Test: `tests/test_config.py`

- [ ] Step 1: Add a failing test for external MCS spectral-efficiency loading
- [ ] Step 2: Run `PYTHONPATH=src python -m unittest tests.test_config.ConfigLoaderTests.test_load_config_supports_external_mcs_table_with_spectral_efficiency -v` and confirm it fails for missing support
- [ ] Step 3: Add the minimal loader implementation in `src/scheduling_sim/config.py`
- [ ] Step 4: Re-run the same test and confirm it passes

### Task 2: Preserve backward compatibility

**Files:**
- Modify: `tests/test_config.py`
- Test: `tests/test_config.py`

- [ ] Step 1: Keep existing inline `mcs_table` test coverage intact
- [ ] Step 2: Run the focused config loader test suite
- [ ] Step 3: Fix only any compatibility break introduced by Task 1
- [ ] Step 4: Re-run the focused suite and confirm all pass

### Task 3: Add new main config artifacts

**Files:**
- Create: `configs/mcs/nr_ul_main.json`
- Create: `configs/target_edge_sensitivity_report_main.json`

- [ ] Step 1: Add the external NR UL MCS spectral-efficiency file
- [ ] Step 2: Add the new main sensitivity config using `237 PRB/U-slot`
- [ ] Step 3: Verify the new config references the MCS file and does not touch old configs

### Task 4: Validate end-to-end loading

**Files:**
- Test: `tests/test_config.py`

- [ ] Step 1: Run `PYTHONPATH=src python -m unittest tests.test_config -v`
- [ ] Step 2: Run `PYTHONPATH=src python -m unittest tests.test_cli.CLITests.test_target_edge_sensitivity_report_script_runs -v`
- [ ] Step 3: Report the new main config path and the exact validation commands used
