# AMHSTrafficLab Public Field and Action Contract

[Platform README](../../README.md)


## 1. Scope

This document organises, by public class, the fields users may read, the extension interfaces they may
implement, and the only legal write channels. Fields are no longer split into separate observation and
condition schemas: `RoutingStrategy`, the dispatcher, routing conditions, Region conditions,
`AreaControlPolicy` and `RebalanceCountScheme` all read the same set of public objects.

Public objects are backed by Cython extensions and reflect the current simulation state. The platform
never implicitly builds a whole-system snapshot per access, and never returns kernel containers, SimPy
objects, live NetworkX objects or C/C++ pointers to users.

## 2. Common rules

| Rule | Contract |
|---|---|
| Object identity | Within one run, a given kernel entity always maps to the same canonical wrapper |
| Collection ordering | OHTs, tasks, nodes, RailPaths and Regions are ordered by stable ID/index |
| Mutability | Fields and public collections are read-only; users cannot add, remove, reorder or replace elements |
| Concurrency visibility | Public callbacks run in well-defined simulation policy stages; within one callback every read sees the same commit point |
| Scalar types | IDs are `str`; times, distances and speeds are Python `float`; counts are Python `int`; booleans are Python `bool` |
| Missing values | Missing objects or IDs use `None`, never `-1`, an empty string or a sentinel object |
| Complexity | Scalar attributes are typically `O(1)`; collection attributes return read-only views; traversal is linear in the element count |
| Writes | Only the immutable actions and policy-stage commands listed here are accepted; every other setter or mutable container is not public |

## 3. `AMHS`

| Field/method | Type | Updated | Read cost | Notes |
|---|---|---|---|---|
| `sim_time` | `float` | Per frame | `O(1)` | Current simulation second |
| `ohts` | `ReadOnlySequence[OHT]` | Entity change | View `O(1)` | Stably ordered by OHT ID |
| `nodes` | `ReadOnlyMapping[str, ControlNode]` | Map load | View `O(1)` | Canonical node wrappers |
| `rail_paths` | `ReadOnlySequence[RailPath]` | Map load | View `O(1)` | Stable RailPath order |
| `transport_tasks` | `ReadOnlySequence[TransportationTask]` | Task generation | View `O(1)` | Every task of the current run; filtering is up to the user |
| `areas` | `ReadOnlySequence[WaterLevelArea]` | Map/config load | View `O(1)` | All runtime Regions |
| `rebalance_areas` | `ReadOnlySequence[WaterLevelArea]` | Config load | View `O(1)` | Enabled with `rebalance_stock is not None`, ordered by `area_index` |
| `graph` | `ReadOnlyGraph` | Map load | `O(1)` | Read-only topology façade; never returns NetworkX objects |
| `get_node(node_id)` | `ControlNode` | — | `O(1)` average | Raises `UnknownNodeError` for unknown IDs |
| `get_oht(oht_id)` | `OHT` | — | `O(1)` average | Raises `UnknownOHTError` for unknown IDs |
| `get_area(area_id)` | `WaterLevelArea` | — | `O(1)` average | Raises `UnknownAreaError` for unknown IDs |

The following methods may only be called during the policy stage of `AreaControlPolicy.execute()`:

| Method | Effect |
|---|---|
| `set_admission(area, mode)` | Requests a public Region admission mode; accepts only `OPEN`, `quota` or `HOLD_NEW_ENTRIES` |
| `clear_admission_override(area)` | Clears the manual mode and restores automatic water-level control |
| `request_rebalance(counts)` | Requests execution of signed Region counts |

Calling them in any other stage raises `PhaseViolationError`. These methods record commands first and are
validated and committed together once the policy returns, so a half-committed state is never exposed.

## 4. `OHT`

| Field | Type | Updated | Cost | Semantics |
|---|---|---|---|---|
| `id` | `str` | Fixed | `O(1)` | Stable ID |
| `status` | `str`/public enum | Event/frame | `O(1)` | Current discrete state |
| `current_node` | `str` | Node arrival | `O(1)` | Actual node ID; mid-rail it keeps the current/nearest node and never returns a ControlNode |
| `path` | `RailPath \| None` | Rail entry | `O(1)` | Current RailPath |
| `x` | `float` | Per frame | `O(1)` | Position on the current path, in m |
| `l` | `float` | Fixed | `O(1)` | Vehicle length, in m |
| `v` | `float` | Per frame | `O(1)` | Current speed, in m/s; keeps the direct OHT field name |
| `current_task` | `TransportationTask \| None` | Task event | `O(1)` | Current transport task |
| `preassigned_task` | `TransportationTask \| None` | Dispatch | `O(1)` | The single task awaiting promotion |
| `target_node` | `str \| None` | Task/cruise/rebalance | `O(1)` | Current routing target |
| `route_anchor` | `str \| None` | Route install/motion | `O(1)` | Semantic start of the current complete route |
| `route` | `ReadOnlyRouteView[str]` | Route replacement | View `O(1)`; traversal `O(L)` | Complete node sequence of the current generation |
| `current_area_ids` | `ReadOnlySet[str]` | Occupancy change | View `O(1)` | Regions the OHT is physically inside |
| `waiting` | `bool` | Resource/car-following | `O(1)` | Whether the OHT is currently waiting |
| `requested_area_ids` | `ReadOnlySet[str]` | Resource | View `O(1)` | Regions with an outstanding request |
| `granted_area_ids` | `ReadOnlySet[str]` | Resource | View `O(1)` | Regions holding an entry grant |

`OHT.route` is a generation-bound immutable view. When the system replaces the underlying route, views
already returned are not modified; a new read returns a new generation. The view provides no `append`,
`extend`, item assignment, `clear` or writable buffer. Users must not set `route`, `target_node`,
`current_node`, `path`, task or resource fields directly.

## 5. `ControlNode`, `RailPath` and the graph façade

### 5.1 `ControlNode`

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable node ID |
| `position` | `ReadOnlySequence[float]` | `[x, y]` map coordinates, in m |
| `type` | public enum/`str` | Node type |
| `is_parking` | `int` | `-1` is not a parking node; `>=0` is the parking priority |
| `is_join`, `is_split` | `int` | Current map flags |
| `incoming_paths` | `ReadOnlySequence[RailPath]` | Incoming edges, stable order |
| `outgoing_paths` | `ReadOnlySequence[RailPath]` | Outgoing edges, stable order |

### 5.2 `RailPath`

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable rail ID |
| `start_node`, `end_node` | `ControlNode` | Canonical node wrappers |
| `length` | `float` | m |
| `max_speed` | `float` | m/s; keeps the direct RailPath field name |
| `weight` | `float` | Current public routing weight; read-only |
| `type`, `direction`, `hid_code` | `str` | Map attributes |
| `status` | `str`/public enum | Public states such as `NORMAL`/`BLOCKED`/`MAINTENANCE` |
| `current_occupancy` | `int` | Current occupancy count |
| `ohts` | `ReadOnlySequence[OHT]` | Current physical order; not modifiable |
| `incoming_paths` | `ReadOnlySequence[RailPath]` | Potentially conflicting incoming rails, read-only |

`ReadOnlyEdge` uses `source_node_id` and `target_node_id`, both `str`. `ReadOnlyGraph` can query nodes,
outgoing edges, incoming edges, neighbours, edge attributes and the
read-only information shortest paths need, and provides
`shortest_path(start_node, target_node) -> list[str]` and
`shortest_distance(start_node, target_node) -> float`. It must never return the underlying
NetworkX object or allow the topology or attributes to be modified.

Path planning uses `graph` as the authoritative source.

Error contract: an unknown node ID raises `UnknownNodeError`; an unreachable route raises `NoRouteError`;
`edge_attribute(u, v, key)` raises `UnknownEdgeError` when the edge does not exist or has no such
attribute. All of these are subclasses of `AMHSLabError` — the public surface never raises kernel
exceptions and never leaks a bare `KeyError`.

## 6. `TransportationTask`

| Field | Type | Updated | Notes |
|---|---|---|---|
| `id` | `str` | Fixed | Stable task ID |
| `start_location` | `str` | Fixed | Pickup node ID |
| `end_location` | `str` | Fixed | Delivery node ID |
| `status` | `CREATED \| PRE_ASSIGNED \| IN_PROGRESS \| COMPLETED \| FAILED` | Task event | Canonical state |
| `create_time` | `float \| None` | Fixed | Simulation creation time, s |
| `start_time` | `float \| None` | Start | Simulation start time, s |
| `pickup_time` | `float \| None` | Pickup | s |
| `end_time` | `float \| None` | Completion/failure | Simulation end time, s |
| `assigned_oht` | `str \| None` | Assign/promotion | ID of the executing OHT; keeps the direct task field name |
| `preassigned_oht` | `str \| None` | Pre-assign/promotion | Reserved OHT ID |
| `foup` | `FOUP` | Fixed | Canonical read-only FOUP wrapper |

Task fields have no public setter. `PRE_ASSIGN` is established by a dispatcher action; promotion, failure
recovery and task routing are performed by the system.

### 6.1 `FOUP`

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable FOUP ID |
| `wafer_count` | `int` | Wafer count |
| `current_location` | `str \| None` | Current node ID |
| `status` | `str`/public enum | Current FOUP status |
| `current_task` | `str \| None` | Current task ID |

FOUP callbacks, process manager references and the internal mutable process route are not exposed on the
public surface.

## 7. `WaterLevelArea`

The public runtime type of an Region is uniformly `WaterLevelArea`.

| Field | Type | Updated | Notes |
|---|---|---|---|
| `id` | `str` | Fixed | Stable Region ID |
| `area_index` | `int` | Fixed | Stable index within one run |
| `node_ids` | `ReadOnlySet[str]` | Config load | Member nodes |
| `entry_edges`, `exit_edges` | `ReadOnlySequence[ReadOnlyEdge]` | Config load | Directed boundaries |
| `capacity` | `int` | Config load | Physical capacity |
| `low_water`, `high_water` | `int` | Config load | Quota and hold levels for automatic control |
| `occupancy` | `int` | Physical occupancy or near-end grant change | Deduplicated count of OHTs physically inside the Region and OHTs holding a grant within the entry control distance |
| `controllable` | `bool` | Config load | Whether the Region accepts a manual admission override (`set_admission`/`clear_admission_override`); does not affect `rebalance_areas` eligibility |
| `admission_mode` | `OPEN \| quota \| HOLD_NEW_ENTRIES` | Automatic/manual control | Current effective public mode; the automatic LOW/MID/HIGH levels map to these three values in order |
| `admission_override` | `OPEN \| quota \| HOLD_NEW_ENTRIES \| None` | Policy commit | Current public manual override; `None` means automatic water-level control |
| `rebalance_stock` | `int \| None` | Config load | `None` means the Region does not take part in rebalancing |
| `members` | `ReadOnlySet[OHT]` | Physical occupancy change | Current physical members; taking the view is `O(1)` and it is not ordered for reads |
| `waiting_queue` | `ReadOnlySequence[AreaWaitingEntry]` | Request, ordering or grant change | Ungranted requests flattened in stable entry order |
| `grants` | `ReadOnlySequence[AreaGrantEntry]` | Grant change | Effective entry grants flattened in stable entry order |
| `next_grant_entry_index` | `int \| None` | Rotation cursor change | Zero-based index into `entry_edges` that the next rotation under `quota` considers first; `None` in other modes or when no entry is available |
| `queue_version`, `grant_version` | `int` | Change in the semantics of the corresponding collection | Consistency and auditing |

An Region maintains a separate distance-ordered queue per directed `entry_edge`. Only the head of each queue
may hold a grant; a grant within the control distance is only exempt from water-level revocation, and when
a nearer effective request from the same entry becomes the head it takes over the grant.

Under `quota`, a far-end grant holder keeps its grant for 15 simulation seconds,
and only the first rebalance after expiry may rotate it by entry; when there is no substitute the
`grant_id` and `granted_time` are kept and one more time slice is granted from that rebalance onwards.
`grant_version` increments when a grant is created, revoked, changes state, or when `rotation_deadline` is
updated or cleared; the mere passage of time does not increment it.

New requests, rerouting migrations, a head entering, the head's release, and occupancy or mode changes all
re-sort immediately; the shared-resource rebalance reviews Regions with requests every 3 simulation
seconds. Reads are never truncated. When a queue or its provider is not ready the call raises
`ResourceUnavailableError` and must never return a fabricated empty queue.

### 7.1 `AreaWaitingEntry`

| Field | Type | Notes |
|---|---|---|
| `request_id` | `int` | ID stable for the lifetime of the request |
| `oht` | `OHT` | Requesting vehicle |
| `request_time` | `float` | s |
| `wait_time` | `float` | Current `sim_time - request_time` |
| `entry_edge` | `ReadOnlyEdge` | The directed Region entry edge it registered on |
| `service_rank` | `int` | Position within its entry queue, `0` being the head |

### 7.2 `AreaGrantEntry`

| Field | Type | Notes |
|---|---|---|
| `grant_id` | `int` | ID stable within one run |
| `oht` | `OHT` | Vehicle holding the grant |
| `granted_time` | `float` | s |
| `age` | `float` | Current `sim_time - granted_time` |
| `rotation_deadline` | `float \| None` | Expiry of the current time slice for a revocable far-end grant under `quota`; `None` for other grants |
| `state` | `RESERVED \| ENTERING` | Grant state; `ENTERING` may exist only briefly within the same kernel call stack |
| `entry_edge` | `ReadOnlyEdge` | The matching directed Region entry edge |

Waiting entries, grants and both collections are immutable and contain no owner dict, callback, event token
or resource container.

## 8. Routing extension contract

### 8.1 `PublicRoutingContext`

| Field | Type | Notes |
|---|---|---|
| `amhs` | `AMHS` | Entry point to the public read-only live objects |
| `graph` | `ReadOnlyGraph` | Read-only graph façade |
| `env` | `ClockView` | Exposes read-only time information such as `now` only; this is not the SimPy env |
| `routing_targets` | `tuple[str, ...]` | Canonical node IDs |
| `alpha`, `gamma`, `tau` | `float` | Profile parameters |
| `extra` | `Mapping[str, object]` | Immutable strategy options |
| `py_rng`, `np_rng` | Strategy-specific RNGs | Isolated from every other RNG stream |

The public context contains no `current_oht`, no kernel logger, no raw NetworkX, no SimPy env and
no mutable graph. The built-in Q/NQ strategies keep their existing private context and need no conversion
to the public façade.

### 8.2 `RoutingStrategy`

```python
class RoutingStrategy(ABC):
    def __init__(self, ctx: PublicRoutingContext, **options): ...
    def init(self) -> None: ...
    def set_decision_context(self, oht) -> None: ...
    def should_replan_at_node(self, node: str, oht) -> bool: ...

    @abstractmethod
    def compute_route(
        self,
        start_node: str,
        target_node: str,
        max_hops: int | None = None,
    ) -> list[str]: ...

    @abstractmethod
    def update(
        self,
        task_id,
        dest_nodes,
        from_node,
        to_node,
        observed_time,
        next_node=None,
        agent_id=None,
    ) -> None: ...

    @abstractmethod
    def estimate_travel_time(
        self,
        start_node: str,
        end_node: str,
    ) -> float: ...

    @abstractmethod
    def estimate_task_time(
        self,
        current_node: str,
        pickup_node: str,
        dropoff_node: str,
    ) -> float: ...
```

`RoutingStrategy.__init__()` stores `self.ctx`; a subclass that overrides the constructor must call
`super().__init__()` or store the same context explicitly. `update()` matches the current Q/NQ
edge-completion call format. The two estimate hooks match the current dispatcher routing-cost call chain;
the return value must satisfy `type(value) is float` and may be a non-negative finite value or `math.inf`
to mark an unreachable pair — negative values, NaN and `-math.inf` are rejected. `get_state()`,
`set_state()`, `get_diagnostics()`, `save_checkpoint()`, `load_checkpoint()` and `close()` are optional
hooks for strategy state; the checkpoint here means algorithm state only, never a
simulation/environment checkpoint.

`compute_route()` must return an exact Python `list` whose elements are exact Python `str`. The sequence
starts at `route_anchor`, ends at `target_node`, and every adjacent pair must have a directed RailPath
between them and satisfy the system safety constraints. The platform performs no node-ID conversion.
`max_hops` is a search-budget hint: a truncated route is not allowed, and it is not an upper bound on the
length of a complete route — the validator will not reject a complete route merely because it exceeds
that hint.

There is no next-hop selection, no `SELECT_NEXT_EDGE`, no candidate path table, no routing mask and no
`WAIT`. Type or signature errors and user exceptions fail immediately and stop the run; a sequence of the
right type but invalid semantics is recorded as an error and goes to the canonical Dijkstra fallback.

`RoutingStrategy` does not define `get_best_action`; `compute_route` is the only route-selection method.
The implementation must remove the kernel's calls to `router.get_best_action(...)`: if a kernel flow only
needs the next edge, it must still call and validate the complete route first and then extract `route[1]`
internally. The built-in Q/NQ strategies may keep per-node selection logic as private helpers, but it must
not become a public method; their private context and the internal learning hooks they need stay
unchanged, with no node-ID or context conversion.

### Vehicle decision hooks and frame observers

`set_decision_context(oht)` is an optional no-op by default. Before vehicle route
computation, node replan checks and edge feedback, it receives the canonical read-only
OHT from the same registry as `ctx.amhs`. One strategy serves multiple vehicles;
the most recent context is not a permanent vehicle assignment. Dispatch cost estimates
do not establish a vehicle decision context.

`should_replan_at_node(node, oht)` defaults to False. It runs at eligible node
departures, including forks, with a string node ID and the canonical read-only OHT.
Its return must satisfy `type(value) is bool`. True requests a complete validated
route even if the current route is valid; False does not suppress system-required
replanning. Waiting vehicles are skipped. Physical movement, admission and safety
checks remain controlled by the platform.

`register_simulation_observer(callback, every_n_frames=1)` accepts a synchronous
callable invoked as `callback(amhs)` and a positive exact Python int interval.
It returns an idempotent unsubscribe function. Each public `run_simulation` snapshots
registrations at entry and invokes them in registration order at completed frames
N, 2N, ... after policy/routing work and clock advancement. There is no time-zero or
partial-final-interval callback. Cadence starts afresh for each run; changes to
registrations affect subsequent runs only.

Observers receive the shared canonical read-only AMHS outside the policy command
stage. Public OHT, task, rail, graph and resource state cannot be mutated through
these views. Return values are ignored; exceptions stop the run and close the router.
Views are live, so history recording must copy needed values. Registrations apply
only to public synchronous runs in the current process; CLI/GUI workers do not
inherit them. See the [manual](../platform/manual.md#vehicle-decisions-and-learning-observations)
for a registration/cleanup example.

### 8.3 Routing conditions

Only these two registered callable forms are accepted:

```python
condition(amhs) -> bool
condition(amhs, oht) -> bool
```

Registration checks the signature, and at runtime an exact Python `bool` is required. A global condition
runs once at each integer simulation second `t=0,1,2,...`; a per-OHT condition runs once per vehicle in
that same second, ordered by stable OHT ID, before the target/eligibility check. While it stays `True` the
complete policy is triggered each second. Conditions only add replanning; they cannot delay routing that
the system requires.

## 9. Dispatch extension contract

```python
dispatcher(
    ohts: ReadOnlySequence[OHT],
    tasks: ReadOnlySequence[TransportationTask],
    cost_estimator: CostEstimator,
) -> list[DispatchAction]
```

`CostEstimator` keeps the current dispatcher callable form:

```python
class CostEstimator(Protocol):
    def __call__(
        self,
        oht: OHT,
        task: TransportationTask,
        /,
    ) -> float: ...
```

The cost of an available OHT follows the current cost mode; the PRE_ASSIGN cost of a busy OHT extends
from the remainder of its current task to the candidate task's completion. The return value is a
non-negative finite `float`, or `math.inf` to mark the pair as infeasible; negative values, NaN and
`-math.inf` are rejected. `math.inf` marks a forbidden pair: ASAP must skip it and the Hungarian cost
matrix must mask it, rather than substituting a large finite number and assigning it. When a task has no
finite candidate it stays pending and no action is produced. The returned actions must be an exact
`list[DispatchAction]`; an empty list means no action.

```python
@dataclass(frozen=True, slots=True)
class DispatchAction:
    kind: DispatchActionKind  # ASSIGN | PRE_ASSIGN
    task: TransportationTask
    oht: OHT
```

There is no `NO_OP`, no cancel, no revoke and no pre-assign method that bypasses the validator. The whole
batch of actions is validated atomically: objects must come from the same AMHS; a task or OHT slot may not
conflict; `ASSIGN` requires the OHT to be currently available; `PRE_ASSIGN` requires the OHT to be
executing a not-yet-finished transport task, the task to be `CREATED`, and both pre-assignment slots to be
empty. If any check fails, nothing in the batch is committed.

Promotion reuses the normal task-start bookkeeping: before the OHT becomes visible to the dispatcher as
available, the system atomically sets `assigned_oht` and `start_time`, clears both pre-assignment slots,
sets the task to `IN_PROGRESS`, records a single task-start event, and then establishes the normal target
and the route it needs. Region/Bay intents count the start/end location of a pre-assigned task once each
under the existing rules, without double counting because both task and OHT slots are set.

## 10. Regional control extension contract

```python
area_condition(amhs) -> bool

class RebalanceCountScheme(ABC):
    @abstractmethod
    def compute(self, amhs: AMHS) -> Mapping[WaterLevelArea, int]: ...

class AreaControlPolicy(ABC):
    @abstractmethod
    def execute(self, amhs: AMHS, rebalance_scheme: RebalanceCountScheme) -> None: ...
```

A Region condition runs once per frame and requires an exact Python `bool`; while
true the complete policy runs once that frame. At the fixed 1/30 s step, one second
executes 30 checks (t=0 through 29/30), and a zero-length run executes none. False
does not clear existing overrides. Rebalance periods and one-shot action deduplication
belong to the policy; routing conditions retain their 1 Hz contract. `RebalanceCountScheme` and the policy may read every public
live object defined in this document.

Counts may cover only a subset of `amhs.rebalance_areas`, with missing entries treated as 0; keys must be
canonical Region wrappers of the same AMHS, and values must satisfy `type(value) is int`, so `bool`, NumPy
scalars and floats are rejected.

Policy-stage commands form one batch once the policy returns: identical commands for the same Region are
collapsed; mutually conflicting mode or count commands fail the whole batch; and all fallible basic
validation and rebalance planning happens before any mutation. The public `AdmissionMode`, the public
fields and user input contain only the three mode values declared in this document; undeclared values
must be rejected.

Implementation limit (2026-09-26): command validation/conflict checks and callback
failures are buffered before writes, but the current executor still plans and installs
vehicle assignments during commit. The stronger planning-before-any-mutation requirement
above is not fully implemented; public-runner acceptance does not certify transaction
rollback on execution-time exceptions. See the platform manual's regional-control limits.

Semantics of the three public modes:

| Mode | Semantics |
| --- | --- |
| `OPEN` | Does not restrict new entry requests and lets the Region's existing arbitration decide |
| `quota` | Rotates the right of way against the remaining quota on a timer (the automatic control result at the mid water level) |
| `HOLD_NEW_ENTRIES` | Admits no new entry requests; held grants and in-Region members are unaffected, and their visibility is expressed by the waiting/grant contract in §7 |

## 11. Capabilities that are not public

- `__dict__` of arbitrary objects, internal pointers, private attributes or dynamic `setattr`;
- NetworkX, SimPy, EventEngine, resource containers and callbacks;
- direct writes to routes, graphs, queues, grants, membership, task mappings or simulation time;
- next-hop selection, route replacement or resource-queue replacement as a user action;
- core source paths, private algorithm tables, industrial data identifiers, and private paths in debug stacks;
- fields or enum values not declared in the versioned documentation.

## 12. Contract tests

At minimum the following must be covered:

1. canonical wrapper identity; only ordered collections keep a stable order, while set views such as `members` promise no iteration order;
2. every public field type, missing value and unit;
3. route-view immutability, stability of the previous generation, and visibility of new reads;
4. failed writes to graph, tasks, queues, grants, Region membership and the clock;
5. both routing-condition signatures, per-second triggering, and behaviour while continuously `True`;
6. stopping the run on a routing return-type error, Dijkstra fallback on invalid semantics, and `NoRouteError` when Dijkstra finds no route;
7. `PRE_ASSIGN` leaving the current task/route untouched, the single-slot constraint, atomic promotion, and failure recovery;
8. Region waiting/grants being complete and separated, preserving provider container order, and raising when the provider is not ready;
9. count subsets, same-AMHS keys, exact ints, and batch conflicts;
10. the three public admission modes, the automatic LOW/MID/HIGH mapping, idempotent repeated commits of the same manual override, and rejection of undeclared modes;
11. `next_grant_entry_index`, `rotation_deadline`, the first rebalance after expiry, renewal without a substitute, and the `grant_version` rules;
12. public behaviour parity between source runs and the Cython wheel;
13. the public repository history and wheel contents carrying no core source or industrial information.
