# AMHSTrafficLab Configuration Reference

[Platform README](../../README.md)


## 1. Configuration structure

```json
{
  "active_sim_profile": "large_300",
  "active_headless_profile": "default_headless",
  "runner_mode": "process",
  "process_transport": {"mode": "shm"},
  "simulation_configs": {
    "large_300": {}
  },
  "headless_run_configs": {
    "default_headless": {}
  }
}
```

`active_sim_profile` is used by the GUI; `active_headless_profile` selects the headless run parameters and
the simulation profile they are linked to. The public `config_validate` entrypoint validates **one profile
JSON** before startup (`amhslab config_validate --config CONFIG`, where CONFIG is a single profile object,
not this multi-profile file); resolving `active_*_profile` into that profile is the caller's job.

## 2. Canonical profile keys

| key | type | Required/default | Notes |
|---|---|---|---|
| `filepath` | `str` | Required | Map workbook |
| `oht_nums` | `int > 0` | Required | Number of OHTs |
| `task_generation_method` | enum | Required | `fixed_ratio/from_to_table/from_data` |
| `task_dispatch_mode` | enum | Required | `asap/batch` |
| `seed` | `int` | profile | Root seed |
| `method` | `str` | profile | Built-in routing code or a user-registered name |
| `cruising_method` | `str` | `None` | Cruising strategy |
| `driveaway_method` | `str` | profile | Drive-away strategy |
| `alpha` | `float` | `0.1` | Routing learning rate |
| `gamma` | `float` | strategy default | Routing discount |
| `tau` | `float` | `0.5` | Routing temperature |
| `scale` | positive float | `0.001` | Map coordinate scale |
| `default_oht_length` | positive float | `1.0` | Vehicle length shared by OHT and Region capacity, in m |
| `max_safe_distance` | nonnegative float | profile | Safety distance, in m |
| `merge_stop_distance` | nonnegative float | profile | Control distance before a merge, in m |
| `merge_release_distance` | nonnegative float | profile | Release distance after a merge, in m |
| `initialize_oht_on_path` | bool | profile | Whether initial vehicles are placed on a RailPath |
| `strict_map_validation` | bool | `false` | When `true`, a dangling rail in the map fails immediately; recommended for formal benchmark runs |
| `merge_grant_selector` | enum | profile | Merge grant strategy |
| `area_control_policy` | str | `None` | Region control policy |
| `enable_area_admission` | bool | `false` | Region admission |
| `water_level_areas` | list | `None` | Inline Region definitions (see section 6) |
| `water_level_area_filepath` | str | `None` | Region catalog workbook (see section 6) |
| `collect_periodic_stats` | bool | `true` | Collect periodic KPI samples |
| `enable_event_record` | bool | `true` | Record the Output-only event stream; `false` speeds up the run |
| `enable_logging` | bool | `true` | File logging |
| `enable_num_lead` | bool | `false` | Leading-vehicle bookkeeping |
| `draw_figure_step` | int | `1000` | GUI figure redraw step |
| `intra_bay_ratio` | float | `0.7` | Intra-Region task share |
| `initialize_oht` | str | `random` | Initial vehicle placement mode |
| `fixed_generation_interval_seconds` | float | `1.0` | `fixed_ratio` trigger interval, in s |
| `fixed_tasks_per_interval` | int | `3` | Tasks per `fixed_ratio` trigger |
| `dispatch_interval` | float | `5` | Batch dispatch interval, in s |
| `loop_length_bound` | int | `None` | Directed-cycle enumeration bound; `None` uses the built-in default |
| `routing_options` | dict | `None` | Strategy options, forwarded to `StrategyClass(context, **options)` |
| `routing_dispatch_cost_mode` | enum | `static_dijkstra` | `router` or `static_dijkstra` |

**The full key set is the kernel constructor's parameter list** (`AMHSSimulation.__init__`),
not this table: `config_validate` takes its known-key set from that signature by
introspection, so a key the constructor does not accept is rejected as unknown. This table
documents the keys the shipped profiles actually use. Per-method routing parameters
(`nq_*`, `cd_*`, `cwd_*`) are accepted by the validator and documented alongside their
methods.

A small number of constructor parameters are **internal to the platform**: a profile may
not set them, and `config_validate` rejects those names explicitly even though the
constructor accepts them. The built-in defaults are what every shipped profile uses.

The configuration key is `task_dispatch_mode`, not `dispatch`, `dispatch_mode` or `task_dispatcher`.

## 3. Task generation

### fixed_ratio

```json
{
  "task_generation_method": "fixed_ratio",
  "fixed_generation_interval_seconds": 1.0,
  "fixed_tasks_per_interval": 2,
  "intra_bay_ratio": 0.7
}
```

### from_to_table

```json
{
  "task_generation_method": "from_to_table",
  "from_to_table_filepath": "tables/example.csv"
}
```

The exact field name for the table path follows the loader and the type stubs, and `config_validate` must
confirm that the file exists and that its columns are valid.

### from_data

Uses an approved data-driven task input. The public distribution contains no industrial task tables;
examples may only reference synthetic or approved fixtures.

An unknown value fails immediately and never falls back to `fixed_ratio`.

## 4. Dispatch

```json
{
  "task_dispatch_mode": "batch",
  "dispatch_interval": 5
}
```

- `batch`: calls the dispatcher at the configured interval;
- `asap`: dispatches as soon as a task and vehicle meet the immediate-trigger condition;
- both modes ultimately share the same action validator/executor;
- default ASAP keeps the current cost-mode selection: router-based mode uses the strategy's estimated task time, while static/no-router mode uses the existing static distance rule; equal costs are broken by the current stable OHT order.

## 5. Routing

`method` may be a built-in registry code or a user-registered name. The built-in codes are reported by the
wheel's registry, so the configuration validator does not hard-code a duplicate list that would easily
drift.

User strategy options are passed as an explicit routing options mapping to:

```python
StrategyClass(public_context, **options)
```

A condition configuration references a registered callable ID and supports:

```text
global:  (amhs) -> bool
per_oht: (amhs, oht) -> bool
scan:    every integer simulation second
```

The configuration accepts no next-hop action, no candidate table, no routing mask and no route setter.

## 6. WaterLevelArea

Regions may be supplied inline through `water_level_areas`, or referenced through
`water_level_area_filepath` as a standalone XLSX catalog; the two must not both provide a non-empty Region
list. An external catalog contains the `Areas` master sheet plus an `AreaTracks` or `AreaNodes`
membership sheet. The rail endpoints of `AreaTracks` and the explicit nodes of `AreaNodes` together form
the runtime node set of an Region.

`map_editor` creates and edits rail-membership catalogs, exporting `Areas` and `AreaTracks`. Every Region
describes at least:

- ID and enabled state;
- rail/node membership;
- low/high water;
- rebalance_stock (may be None).

Inline configuration may additionally provide `controllable` (it only governs the manual admission
override and does not affect rebalance eligibility), `edges` or other runtime construction fields. At
runtime the entry/exit edges are derived from the active map and the physical capacity is recomputed. The
full XLSX fields and constraints are in the
[Region Excel Data Dictionary](region-workbook.md).

`config_validate` checks Region IDs, enabled/controllable types, membership references, water level and
capacity, and duplicate membership. Runtime Regions are uniformly `WaterLevelArea`.

An Region condition references a registered `(amhs)->bool` callable and runs at each integer simulation
second. A policy or scheme Python class or registry ID must resolve successfully at startup.

## 7. CLI overrides

```bash
amhslab config_validate --config experiments/base_config.json --map experiments/maps/small_150.xlsx
amhslab headless --config experiments/base_config.json --map experiments/maps/small_150.xlsx
```

Override order:

1. read the configuration;
2. select the active/profile entry;
3. apply explicit CLI overrides;
4. validate the final values;
5. construct the `AMHSSimulation`.

`--map` overrides `filepath` only; it does not modify the configuration file itself.

## 8. Headless run config

| key | type | Notes |
|---|---|---|
| `runs` | positive int | Number of runs |
| `workers` | nonnegative int | Number of workers; the semantics of 0 are given in the entrypoint documentation |
| `until` | positive float | Simulation seconds |
| `speed` | positive number | Run-speed parameter |
| `output_dir` | str | Output directory |
| `export_output` | bool | Whether to export |

An output directory is never added to the public release allowlist unless it is a separately approved
synthetic fixture.

## 9. Validation errors

The following fail before startup:

- an unknown top-level or profile key, except explicitly allowed documentation metadata keys such as `_comment`;
- a profile that does not exist;
- an imprecise type, or a value that is not finite or is out of range;
- an unknown task generation or dispatch enum;
- a missing map or task table;
- an invalid Region reference, direction or water level;
- an unregistered user strategy, dispatcher, condition, policy or scheme, or one with a bad signature;
- a CPython or wheel platform mismatch.

Error messages include the JSON path, the actual value, the expected type or enum, and a fix hint, but must
never leak private build paths or kernel stacks.

Internal traffic-admission switches are platform-managed and are not public
configuration fields. Public entrypoints reject profiles that attempt to set them.
Region control remains configurable through `area_control_policy`.
