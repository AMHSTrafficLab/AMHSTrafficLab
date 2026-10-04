# AMHSTrafficLab Platform Contract

[Platform README](../../README.md)


## 1. Goal

AMHSTrafficLab is released as one fresh public Git repository. Users install the compiled Cython wheel
and use the platform through the public Python API, the command-line entrypoints, the user-inheritable
ABCs and the documentation. The public release does not depend on Gymnasium, PettingZoo or any other
reinforcement-learning environment standard.

The platform keeps updating internal motion and resource state at `1/30 s`. User routing conditions are evaluated
once at each integer simulation second `t=0,1,2,...`; user Region conditions are evaluated
every frame. System events such as new
tasks, invalidated routes and safety recovery still execute immediately and do not wait for the condition
scan.

### 1.1 Terminology

The accompanying paper uses **region** and **regional control** for what this repository calls an
Area: the `WaterLevelArea` runtime type, the `Areas` catalog sheet, the `AreaID` column and the
`area_control_policy` profile key. Those names are data and configuration contracts referenced by
existing maps, catalogs and profiles, so they are kept unchanged. This documentation and the other
public documents use the paper's wording — *region*, *regions*, *regional control* — in prose, and
`region` always means the platform's Area.

The third public admission mode is named **quota**, matching the paper, and `admission_mode`
reports that same value. The two automatic thresholds are the **quota level** — the
`ReopenLevel` catalog column and the `low_water` field, where quota control starts — and the
**hold level** — the `WaterLevel` catalog column and the `high_water` field, where new entries
are held. `CloseLevel` is an audit column that normally restates the hold level. These column
and field names are data and configuration contracts, so they are kept unchanged.

## 2. Distribution

Install the compiled wheel. The public Python API is included in that installation;
no additional source package or editable install is required. Documentation,
examples, benchmark inputs and evaluation scripts accompany the wheel. Model
checkpoints are separate downloads.

## 3. Supported platform

Linux x86_64 and CPython 3.11 are supported by this release. See the
[installation guide](../getting-started/installation.md) for system libraries and
the selected release files.

## 4. Entrypoints

The public package promises only these six stable entrypoint IDs:

| ID | Purpose |
|---|---|
| `environment_check` | Checks Python, the wheel tag, dependencies and runtime libraries |
| `config_validate` | Validates the configuration and map references without starting a simulation |
| `gui` | Starts a GUI simulation |
| `headless` | Starts a headless simulation |
| `map_editor` | Starts the map and WaterLevelArea editor |
| `benchmark` | Runs platform and packaging benchmarks |

The CLI form is `amhslab <entrypoint-id> ...`. On the Python side the same registry can be queried and
invoked. An entrypoint must not depend on core source files in the public repository.

## 5. Configuration

The core keys of the current profile match the code:

```json
{
  "filepath": "experiments/maps/small_150.xlsx",
  "oht_nums": 150,
  "task_generation_method": "fixed_ratio",
  "task_dispatch_mode": "batch"
}
```

- `task_generation_method`: `fixed_ratio | from_to_table | from_data`;
- `task_dispatch_mode`: `asap | batch`;
- internal traffic-admission switches are platform-managed and cannot be set by public profiles;
- the CLI `--map` option overrides the profile's `filepath`;
- unknown keys, unknown enums, missing files and type errors are reported directly by `config_validate`.

## 6. Public live objects and the read-only boundary

Users can read the Cython-backed AMHS, OHT, RailPath, ControlNode, TransportationTask and WaterLevelArea
live objects at low latency. Public collections and objects keep a stable identity within one run, and the
complete system state is never implicitly copied per call.

Reads must be transparent and cheap; writes are only allowed through explicit, verifiable command
interfaces. The following data must not be modified directly by users:

- OHT routes, current position, tasks and status;
- the rail graph, node connectivity and RailPath geometry;
- task lifecycles and the assignment/pre-assignment mapping;
- Resource/Region waiting queues, grants, membership and capacity;
- the simulation clock, EventEngine, SimPy structures and internal callbacks.

`OHT.route` returns a generation-bound immutable read-only view: reading an attribute is `O(1)`; after the
system replaces the route, a view already obtained still points stably at the route it was taken from,
while a new read gets the new route; traversal is `O(L)`. Every route update can only be performed by the
system validator and installer.

See [Field_Whitelist.md](field-reference.md) for the complete fields and complexities.

## 7. Routing

A user registers a complete `RoutingStrategy` class. The platform creates one AMHS-shared instance
following the construction and lifecycle style of the current built-in Q-routing/NQ-routing:

```python
router = StrategyClass(context, **options)
router.init()
route = router.compute_route(start_node, target_node, max_hops=None)
```

A public strategy outputs only one complete `list[str]`. It provides no `SELECT_NEXT_EDGE`, no next-hop
selection, no candidate path table, no routing action mask and no `WAIT` action. Node IDs are not
converted; input and output use the canonical string IDs from the map.

`get_best_action` is removed from `RoutingStrategy`; every routing call in the kernel uses `compute_route`
uniformly. When an internal flow needs only the next edge, it must still validate the complete path first
and let the system extract the edge internally. The built-in Q/NQ strategies keep their existing private
context and internal learning hooks, with no conversion. `max_hops` is only a search-budget hint: a
truncated route must never be returned on its strength, and it is not an upper bound on the length of a
complete route.

A strategy exception, or a return type or element type that does not match the contract, stops the run with
an error. When the returned type is right but the route semantics are invalid, the platform records a
structured error and computes a complete fallback with the system Dijkstra; if Dijkstra also finds no path,
it stops the affected OHT safely and terminates the run with `NoRouteError`. The platform copies the
returned array defensively before installing it.

System-required routing runs immediately for a new task or target, an empty route, an inconsistent anchor,
an invalidated current path and safety recovery. A user bool condition only adds replanning:

- `(amhs) -> bool`: runs once every integer simulation second; while true it runs the complete policy for every OHT that has a target and meets the replanning conditions, ordered by stable ID;
- `(amhs, oht) -> bool`: runs once per OHT per integer simulation second, ordered by stable ID, before deciding whether that vehicle meets the replanning conditions;
- while a condition stays `True`, the complete routing policy runs again every second;
- the return value must be an exact Python `bool`; a bad signature or return type fails immediately.

## 8. Dispatching and `PRE_ASSIGN`

The custom dispatcher format is:

```python
dispatcher(ohts, tasks, cost_estimator) -> list[DispatchAction]
```

`cost_estimator(oht, task) -> float` keeps the current callable shape; it returns a non-negative finite
value, or `math.inf` to mark a forbidden pair. A busy OHT's estimate covers the remainder of its current
task plus the candidate task; both ASAP and the Hungarian solver must skip a forbidden pair.

`DispatchAction` is immutable, the only actions are `ASSIGN` and `PRE_ASSIGN`, and an empty list means no
action this time. The whole batch of actions is validated first and then committed once; if any action is
illegal, nothing in the batch takes effect.

`PRE_ASSIGN(task, oht)` may only reserve a `CREATED` task for an OHT that has not yet finished its current
transport task. Each OHT and each task has at most one pre-assignment slot. It does not modify the current
task, status, target, route or resource reservation. When the current task completes, the system promotes
the pre-assigned task atomically before the OHT becomes visible to the dispatcher as available:

```text
CREATED -> PRE_ASSIGNED -> IN_PROGRESS
```

Promotion sets `assigned_oht` and `start_time` in the same atomic stage, clears both directions of the
pre-assignment, records one task-start event, and then establishes the normal target and the route it needs.
Region/Bay intents count the start/end location of a future task once each under the existing rules, without
double counting because both slots are set.

If the OHT fails before promotion, or the current task fails, the system clears both mappings and restores
the task deterministically to `CREATED` and pending.

## 9. Regional control

A runtime Region is a `WaterLevelArea`. Users can create, read and modify Regions and their water-level
configuration through `map_editor`. `controllable` only indicates whether an Region accepts a manual
admission override; it neither decides whether the Region enters `rebalance_areas` nor blocks
`request_rebalance`.

An Region maintains a distance-ordered queue per directed entry edge, and only the head of each entry may hold
a grant. Under `quota`, a grant outside the control zone runs in 15-simulation-second
rounds, and after expiry it swaps one-for-one with the heads of the other entries; without a substitute the
original grant is kept and renewed for one more time slice. `next_grant_entry_index` indicates the entry the
next round considers first, and a grant's `rotation_deadline` indicates the expiry of its current time
slice.

A new request, a reroute, entering the Region, a release, and occupancy or mode changes all rebalance
immediately, while the shared-resource event reviews Regions with requests every 3 simulation seconds. The
public waiting queue and grants are expanded in stable entry order into complete, separate, immutable
read-only views.

A user Region condition has the form `(amhs) -> bool` and is evaluated every frame;
while it stays true the complete `AreaControlPolicy` runs once per frame (30 Hz at the
fixed 1/30 s step). False does not clear admission overrides; the policy controls its
own rebalance period. Routing conditions retain their separate 1 Hz cadence. A user scheme can read the AMHS,
WaterLevelAreas and other public live objects of the same run directly.

```python
class RebalanceCountScheme(ABC):
    def compute(self, amhs) -> Mapping[WaterLevelArea, int]: ...

class AreaControlPolicy(ABC):
    def execute(self, amhs, rebalance_scheme) -> None: ...
```

`compute()` may return a subset of `amhs.rebalance_areas`, with an Region that does not appear treated as 0.
Keys must be canonical WaterLevelArea objects of the same AMHS, and values must be exact Python `int`s that
may be positive, zero or negative; `bool` is rejected.

Only the following are open during the policy execution stage:

```python
amhs.set_admission(area, mode)
amhs.clear_admission_override(area)
amhs.request_rebalance(counts)
```

The public admission modes are `OPEN`, `quota` and `HOLD_NEW_ENTRIES`. `low_water` is
the quota level and `high_water` is the hold level; the automatic water level applies those three modes in
order for `occupancy < low_water`, `low_water <= occupancy < high_water` and `occupancy >= high_water`.
`set_admission()` accepts the same three values and installs a persistent override, while
`clear_admission_override()` restores automatic water-level control. Undeclared values are rejected during
validation, and users do not submit routes, next hops or individual grant operations.

## 10. Same-second public policy order

Within each frame the public policies read and commit state in this order:

1. process due events;
2. update vehicle motion;
3. update OHT discrete state, and run automatic Region admission on physical occupancy changes — the frame's routing decisions are taken in this step;
4. run the internal route-away sweep;
5. run ASAP dispatch;
6. run the Region rebalancing controller;
7. on integer-second crossings, collect the public routing-condition triggers using pre-Region state;
8. run the public Region policy stage: evaluate its bool condition and commit the policy batch;
9. apply collected public routing triggers against updated targets/eligibility;
10. advance time/frames;
11. in the public synchronous runner, notify due observers with the canonical read-only AMHS.

System-required routing in step 3 remains before the Region stage. Public condition-triggered
replanning in step 9 sees the committed Region state, uses the current rail's endpoint
for a moving vehicle, and does not change its physical position. This is the same frame;
future motion uses the installed route. The internal sweep keeps its existing position
in the frame. Custom regional control disables the built-in rebalancer by requiring the
hold profile; it does not run two independent rebalancers in steps 6 and 8.

## 11. Scope of this release

The distribution provides the simulation platform, public extension interfaces,
examples and tools for the classical and learned main experiment matrices.
Training, transfer evaluation, simulation checkpoint/restore/fork and deterministic
replay are not included in the reproduction workflow.

See [Field_Whitelist.md](field-reference.md) for fields and actions, and
[release information](../release/release-notes.md) for validation coverage.

### Optional learning hooks and state observers

Public strategies may override `set_decision_context(oht)` (default no-op) and
`should_replan_at_node(node, oht)` (default False). The adapter forwards canonical
read-only OHTs, never kernel vehicles; node results must be exact Python bools.
A True requests a complete validated route at a node departure. System-required
replanning and built-in strategy behavior retain their existing paths.

`register_simulation_observer(callback, every_n_frames=1)` returns an idempotent
unsubscribe function. Public runs snapshot registrations and invoke them after N,
2N, ... completed frames, after clock advancement, in registration order. The same
read-only AMHS is shared across callbacks and policies. Callback exceptions propagate
and close the router; return values are ignored. Registrations affect subsequent
public runs in the current process only. See the platform manual for lifecycle and
checkpoint examples.
