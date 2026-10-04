# AMHSTrafficLab Platform Manual

[Platform README](../../README.md)


## 1. Platform capabilities

AMHSTrafficLab simulates AMHS rail networks, OHT motion, transport tasks, complete path planning, task
dispatching, WaterLevelArea admission and rebalancing, a GUI, headless runs and map editing.

Internal motion updates at `1/30 s`. Public user code calls in through the Cython wheel and neither needs
nor can read the core source. Public policies and the internal route-away sweep commit at the end of a
frame, so the bound on their effect over route selection is one frame (`1/30 s`).

## 2. Supported environment and installation

The first public release provides only a CPython 3.11 wheel for the frozen reference platform:

Linux x86_64 requires glibc >= 2.34 and libstdc++ exporting `GLIBCXX_3.4.30`
for DearPyGui 2.3.1. The wheel tag does not express the C++ runtime requirement.

```text
Requires-Python: >=3.11,<3.12
distribution: wheel only
sdist: unavailable
```

Follow the [installation guide](../getting-started/installation.md) from the
extracted release root. It covers the wheel, system libraries and additional
reproduction dependencies. Install from the supplied wheel; no source build is required.

Custom routing is available through `amhslab.RoutingStrategy`,
`register_routing_strategy(name, StrategyClass, conditions=...)` and the synchronous
`run_simulation(config_path, until=..., method=...)` runner. Registration is local to
that Python process; it is not a GUI worker/plugin discovery mechanism. See the
[routing guide](../extensions/routing.md#9-minimal-example) and
[public interface contract](../api/platform-contract.md).

## 3. The six entrypoints

| ID | Command | Notes |
|---|---|---|
| `environment_check` | `amhslab environment_check` | Checks Python, wheel and dependency metadata; native imports require a separate check |
| `config_validate` | `amhslab config_validate --config CONFIG` | Validates the configuration and map references |
| `gui` | `amhslab gui --config CONFIG` | GUI simulation. `--check` loads the profile and the map model, then exits without opening a window |
| `headless` | `amhslab headless --config CONFIG` | Headless simulation. `--until SECONDS` sets the horizon and `--out DIR` also exports the run; the KPI summary is printed either way |
| `map_editor` | `amhslab map_editor [--map PATH]` | Map and WaterLevelArea editing. `--map` opens that workbook; without it the editor starts empty and `File → Open` loads one. `--check` loads the map model and builds the editor, then exits without opening a window |
| `benchmark` | `amhslab benchmark` | Platform/package self-check and micro-benchmarks; needs no map, and reports the installation verdict as a fact while `environment_check` remains the gate |

`CONFIG` is a single profile JSON, never the multi-profile file (`config_validate` rejects that
form by name). Relative paths inside a profile resolve against the working directory, exactly as
the kernel opens the map workbook.

The window entrypoints (`gui`, `map_editor`) need a display. Both take `--check` for the
release smoke and for CI: they import the GUI stack, run the profile through the kernel or
load the map workbook into the editor's model, and stop before the render loop. Rendering is verified separately with a real display; the candidate acceptance
record distinguishes automated window checks from manual editor operation.

`benchmark` does not train the paper algorithms. The public Python API can query the same entrypoint
registry, and the entrypoint IDs must match the CLI exactly.

## 4. Configuration

Configuration is organised into profiles. Core fields:

| key | type | Value/semantics |
|---|---|---|
| `filepath` | `str` | Map workbook path |
| `oht_nums` | `int` | Number of OHTs |
| `task_generation_method` | `str` | `fixed_ratio/from_to_table/from_data` |
| `task_dispatch_mode` | `str` | `asap/batch` |
| `method` | `str` | Built-in routing method or a user-registered name |
| `alpha/gamma/tau` | `float` | Routing parameters |

The CLI `--map PATH` overrides `filepath` in the selected profile. `config_validate` reports unknown
keys or enums, wrong types, missing files, invalid Region references and illegal water levels.

See [conf/CONFIG_README.md](configuration.md) for the full field list.

## 5. Maps and Regions

Maps are Excel workbooks. A minimal rail map needs:

- `ControlNode`: at least ID, x, y and type;
- `Rail`: at least ID, start node, end node and speed limit.

`map_editor` is used to:

- select physical rails on a read-only map;
- create, read, focus, edit and delete WaterLevelAreas;
- set the Region ID, water level, quota level and rebalance stock;
- export Regions as the `Areas` and `AreaTracks` worksheets;
- display and modify Regions as rail membership in the editor.

A node selection helps with map browsing, but the exported Region members contain physical rails only. At
runtime the nodes, entries and exits are derived from both endpoints of every member rail. The full XLSX
field definitions are in the
[Region Excel Data Dictionary](region-workbook.md).

The GUI and headless runs use the same loader for maps and Region configuration.

## 6. Public live objects

User extensions can read directly:

- `AMHS`;
- `OHT`;
- `ControlNode`;
- `RailPath`;
- `TransportationTask`;
- `WaterLevelArea`;
- the graph read-only façade;
- Region waiting entries and grants.

The objects are Cython-backed read-only live wrappers. A given entity keeps its canonical identity for the
whole run; reading a scalar is typically `O(1)`, and the whole system is never implicitly copied per
callback.

### 6.1 OHT route

`OHT.route` is visible in every user callback, not only during routing calls. It returns a
generation-bound immutable complete node sequence:

- taking the view is `O(1)`;
- traversal is `O(L)`;
- after the system replaces the route, an old view keeps its original contents;
- a new read returns a new generation;
- users cannot append to, item-assign, clear or replace the route.

`OHT.current_node` is the actual node ID `str`; mid-edge it keeps the current/nearest node. Planning uses
`route_anchor`. `RailPath.start_node/end_node` return canonical ControlNode wrappers.

### 6.2 Resource queue

`WaterLevelArea.waiting_queue` and `grants`:

- come from the real provider;
- are returned complete, never truncated;
- waiting preserves the provider container's current order and promises neither FIFO nor a fixed priority;
- are kept separate from grants;
- are read-only;
- raise explicitly when the provider is not ready.

## 7. Custom RoutingStrategy

```python
from amhslab import RoutingStrategy

class MyRouting(RoutingStrategy):
    def __init__(self, ctx, **options):
        self.ctx = ctx

    def init(self):
        pass

    def compute_route(
        self, start_node, target_node, max_hops=None
    ) -> list[str]:
        return self.ctx.graph.shortest_path(start_node, target_node)

    def update(
        self, task_id, dest_nodes, from_node, to_node,
        observed_time, next_node=None, agent_id=None,
    ):
        pass

    def estimate_travel_time(self, start_node, end_node) -> float:
        return float(self.ctx.graph.shortest_distance(start_node, end_node))

    def estimate_task_time(
        self, current_node, pickup_node, dropoff_node
    ) -> float:
        return self.estimate_travel_time(current_node, pickup_node) + \
            self.estimate_travel_time(pickup_node, dropoff_node)
```

The system uses `StrategyClass(ctx, **options); init()`, with one shared strategy instance per AMHS. The
public context provides the read-only AMHS, the graph façade, a ClockView, routing targets,
alpha/gamma/tau, immutable options and a strategy RNG. `RoutingStrategy` contains no `get_best_action`; the
kernel calls `compute_route` uniformly and, when it needs only the next edge, extracts it internally after
validating the complete route. The built-in Q/NQ strategies keep their private context and internal
learning hooks.

The system calls the two estimate hooks only when router-based dispatch cost is enabled in the
configuration; their return value must be an exact Python `float`, may use `math.inf` to mark an
unreachable pair, and rejects negative values, NaN and `-math.inf`.

Routing accepts exactly one complete `list[str]` and provides no next hop, no `SELECT_NEXT_EDGE`, no
candidate, no mask and no WAIT. The platform does not convert node IDs.

`max_hops` is only a search-budget hint: a truncated route must never be returned on its strength, and a
complete route is not rejected by the validator merely because it exceeds that hint.

### Vehicle decisions and learning observations

Two optional hooks support vehicle-specific learning:

```python
# Methods on a user RoutingStrategy subclass:
def set_decision_context(self, oht):
    self.decision_oht = oht  # canonical read-only live view

def should_replan_at_node(self, node, oht):
    return len(self.ctx.graph.neighbors(node)) > 1
```

The platform calls `set_decision_context` before vehicle route computation, node
replan checks and edge feedback. One strategy serves all vehicles: the context can
change between calls and must not be treated as a fixed vehicle assignment. Cost
estimates are not vehicle route decisions and do not establish this context.

`should_replan_at_node` is called at eligible node departures, including forks;
waiting vehicles are skipped. Its default is `False`. Returning exact Python `True`
requests a new complete route through the existing validator, even when the old
route is valid. `numpy.bool_`, integers and other non-bool returns stop the run.
Returning `False` does not suppress system-required replanning for missing/stale
routes. This hook does not move vehicles or bypass admission/queue checks.

For general state observation, register a synchronous callback before running:

```python
from amhslab import register_simulation_observer, run_simulation

samples = []
unsubscribe = register_simulation_observer(
    lambda amhs: samples.append((amhs.sim_time, len(amhs.transport_tasks))),
    every_n_frames=30,
)
try:
    result = run_simulation("experiments/base_config.json", until=10)
finally:
    unsubscribe()
```

Callbacks run in registration order after every N completed frames (N, 2N, ...),
after policies, routing and the clock advance. N must be a positive Python integer;
there is no time-zero callback or callback for a final incomplete interval. They
receive the same canonical read-only AMHS used by routing and regional policies.
To retain history, copy the scalar values you need: retaining a view retains live
state. Callbacks have no command stage and cannot write through the public views.
Their return value is ignored; an exception stops the run and closes the router.

Registrations are process-local and apply to subsequent `run_simulation` calls,
including built-in routing runs. Each run snapshots registrations at entry and
restarts frame cadence at zero; registering/unsubscribing during a callback affects
later runs only. Unsubscribe is idempotent. CLI/GUI workers do not automatically
inherit registrations. Use separate processes for independent parallel experiments.

Checkpoint files remain algorithm-owned: load in strategy construction or `init`,
save through your strategy, and explicitly disable learning updates for frozen
evaluation. The public learning integration test exercises real edge feedback,
checkpoint round-trip, frozen evaluation, vehicle identity and fork replanning.

### 7.1 Route errors

- a user exception, or a bad signature or return format: stop the run and report the error;
- an exact `list[str]` with invalid semantics: record it structurally and run the Dijkstra fallback;
- Dijkstra finds no route: install no partial route, stop the OHT safely, and raise `NoRouteError`.

### 7.2 Routing conditions

Supported:

```python
def global_condition(amhs) -> bool: ...
def per_oht_condition(amhs, oht) -> bool: ...
```

The signature is checked at registration, and at runtime an exact Python `bool` is required. The condition
is evaluated at every integer simulation second; while it stays true the complete policy runs each second.
The per-OHT form is evaluated for every OHT. New tasks, targets, empty routes, invalidated routes and
safety recovery do not wait for a condition.

## 8. Custom Dispatch

```python
def dispatch(ohts, tasks, cost_estimator):
    return [
        DispatchAction(DispatchActionKind.ASSIGN, task, oht),
        DispatchAction(DispatchActionKind.PRE_ASSIGN, next_task, busy_oht),
    ]
```

The only actions are `ASSIGN` and `PRE_ASSIGN`; an empty list means no action. The whole batch is validated
first and then committed atomically.

`cost_estimator(oht, task) -> float` keeps the current callable shape. An available OHT is valued by the
current cost mode; the PRE_ASSIGN cost of a busy OHT includes the remainder of its current task.
`math.inf` marks a forbidden pair that both ASAP and the Hungarian solver must skip; negative values, NaN
and `-math.inf` are errors.

`PRE_ASSIGN`:

- reserves one `CREATED` task for an OHT that is executing a not-yet-finished transport task;
- gives every OHT and every task one pre-assignment slot;
- changes no current task, status, target, route or reservation;
- after the current task completes, and before the OHT becomes available to the dispatcher, promotes the reservation atomically: it sets `assigned_oht`/`start_time`, clears both slots, records one task-start event, and then establishes the target and the route it needs;
- on a failure before promotion, clears both mappings and restores the task to `CREATED`/pending.

Region/Bay intents count the start/end location of a future task once each under the existing rules, without
double counting because both slots are set.

The configuration key is `task_dispatch_mode`, with the values `asap` or `batch`.

## 9. Custom regional control

Custom regional control runs through `run_simulation` in the current process. Pass
`area_condition`, `area_policy` and `rebalance_scheme` together. Use
`area_control_policy: "fixed_water_level_hold"` in the profile; workbook stock fields
are loaded without starting the built-in rebalancer. Other control modes are rejected
when these extension objects are supplied. Fresh policy/scheme instances keep user
state independent across runs; the platform creates a fresh stage and shared read-only
views for each run. These Python objects are not JSON settings or CLI/GUI worker plugins.

The following sections give the complete condition, count-scheme and policy pattern.
Use a profile whose map or `water_level_area_filepath` defines Regions and whose
`area_control_policy` is `fixed_water_level_hold`.

### 9.1 Condition

```python
def area_condition(amhs) -> bool:
    # Keep checking so persistent HOLD overrides can be cleared at low water.
    return True
```

Evaluated every frame; while it stays true the complete policy runs each frame
(30 Hz at the fixed 1/30 s step). False does not clear existing overrides. Routing
conditions remain at 1 Hz. Policies control rebalance cadence independently: the
public example checks admission every frame but submits rebalance requests at
0, 5, 10, ... seconds, with tolerance and deduplication. A 20-second run has 600
condition/policy calls and four rebalance calls, with no extra call at t=20.

### 9.2 RebalanceCountScheme

```python
class MyScheme(RebalanceCountScheme):
    def compute(self, amhs):
        return {
            area: area.rebalance_stock - area.occupancy
            for area in amhs.rebalance_areas
        }
```

The returned mapping may be a subset of `amhs.rebalance_areas`, with missing entries treated as 0. Keys
must come from the same AMHS; values must be exact Python ints and may be positive, zero or negative.

### 9.3 AreaControlPolicy

```python
class MyPolicy(AreaControlPolicy):
    def __init__(self):
        self.next_rebalance_time = 0.0

    def execute(self, amhs, rebalance_scheme):
        for area in amhs.areas:
            if not area.controllable:
                continue
            if area.occupancy >= area.high_water:
                amhs.set_admission(
                    area,
                    AdmissionMode.HOLD_NEW_ENTRIES,
                )
            elif area.occupancy <= area.low_water:
                amhs.clear_admission_override(area)
        if amhs.sim_time + 1e-9 >= self.next_rebalance_time:
            amhs.request_rebalance(rebalance_scheme.compute(amhs))
            while self.next_rebalance_time <= amhs.sim_time + 1e-9:
                self.next_rebalance_time += 5.0
```

Pass the three objects to the public runner (import the classes and runner from `amhslab`):

```python
result = run_simulation(
    "path/to/your_region_config.json", until=20,
    area_condition=area_condition, area_policy=MyPolicy(), rebalance_scheme=MyScheme(),
)
```

The count formula above is a simple user policy, not the built-in `F + Q - I - A`
formula. Occupancy includes near-entry grant holders and is not idle-vehicle supply.
Counts request transfers; eligible vehicles, reachability and in-flight commitments
can limit what the platform actually executes. `QUOTA` selects the existing water-level
quota mechanism, not a user-specified numeric quota.

Callback exceptions and command-validation errors occur before commit. Once the kernel
executor starts installing assignments, execution-time errors do not guarantee full
rollback.

The write methods are available only during the policy stage. The public modes are:

- `OPEN`: grants entry to the effective head of each entry queue;
- `quota`: grants against the mid water level quota, rotating revocable far-end grants between entries in 15-simulation-second time slices;
- `HOLD_NEW_ENTRIES`: keeps protected grants and suspends new grants.

`set_admission()` installs a persistent override, and `clear_admission_override()` restores the automatic
state determined by occupancy and the low/high water levels. Users can read
`WaterLevelArea.next_grant_entry_index` and `AreaGrantEntry.rotation_deadline`, but do not submit routes,
next hops or grant operations.

## 10. Limits on state writes

The following are unsupported and must raise:

- setting `oht.route/current_node/path/target/task`;
- modifying nodes, rails or the graph;
- modifying task status or assignment;
- modifying Region members, waiting, grants or capacity;
- modifying the simulation clock or EventEngine;
- accessing raw NetworkX/SimPy;
- obtaining a writable memory view or a kernel pointer from a public object.

## 11. Algorithm state

A RoutingStrategy may provide `get_state/set_state/save_checkpoint/load_checkpoint` to persist its own
learning state. This does not save the simulation world, OHTs, tasks, events, Region queues or execution
time; the platform promises no simulation/environment checkpoint, restore or fork.

## 12. Troubleshooting

### The wheel will not install

Run `amhslab environment_check` and check Python 3.11, the OS/architecture and the wheel tag. Do not try to
compile from the public repository source.

### Config validation fails

Confirm that `task_dispatch_mode` is used, and check the `task_generation_method` enum, `filepath`, the
`--map` override and the Region references.

### A user condition raises

Routing allows one or two parameters, an Region condition only one; both must return an exact Python bool.

### Routing fallback

Look at the structured routing error. A format error never falls back; only a `list[str]` of the right type
but invalid semantics uses Dijkstra. `NoRouteError` means the fallback found no complete route either.

### An Region entry keeps waiting

Check the public admission mode, waiting/grants, occupancy and high water. Do not modify the queue or route
directly.

## 13. Further reading

- [Public field and action contract](../api/field-reference.md)
- [Routing](../extensions/routing.md)
- [Dispatching](../extensions/dispatch.md)
- [Regional control](../extensions/region-control.md)
- [Admission](admission.md)

Internal traffic-admission switches are platform-managed and are not public
configuration fields. Public entrypoints reject profiles that attempt to set them.
Region control remains configurable through `area_control_policy`.
