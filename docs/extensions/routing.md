# Routing extension interface

[Platform README](../../README.md)


## Built-in benchmark methods

The paper's main table uses these 13 methods, readable in code through
`algorithms.routing.PAPER_MAIN_METHODS`:

`D, KD, CD, PFD, EDR, CBR, QLBWR, QECV, BRQ, NQ, DQN, GDQN, MAPPO`

`Q` and `SCD` are kept as extra baselines, readable through
`algorithms.routing.EXTRA_BASELINE_METHODS`, and are not part of the paper's main table.

Learning methods are supplied to benchmark users as black-box checkpoints. For evaluation, turn training
off and load the frozen policy through the checkpoint parameter:

| Method | Evaluation switch | Checkpoint parameter |
|---|---|---|
| Q | `q_training: false` | `q_prior_path` |
| QLBWR | `qlbwr_training: false` | `qlbwr_prior_path` |
| QECV | `qecv_training: false` | `qecv_prior_path` |
| BRQ | `q_training: false` | `q_prior_path` |
| NQ | `nq_training: false` | `nq_prior_path` |
| DQN | `dqn_training: false` | `dqn_prior_path` |
| GDQN | `dqn_training: false` | `dqn_prior_path` |
| MAPPO | `mappo_training: false` | `mappo_prior_path` |

Once unpacked, the checkpoint bundle belongs under `models/routing_final_20260919/`, with file names of the
form `{scenario_family}_{method}.{extension}` and scenario families `s100_2400`, `s150_3120`, `m175_4850`,
`m200_5350`, `m225_6100`, `l275_6850` and `l300_7350`; tabular Q methods use `.json`, NQ/DQN/GDQN use
`.npz`, and MAPPO uses `.pt`. Checkpoints do not enter the Git history; they are published as a separate
resource bundle alongside the benchmark release.

The paper's main evaluation configurations are:

- `experiments/routing_iclr_main13_classical_20000s_seeds0_9.yaml`
- `experiments/routing_iclr_main13_learned_20000s_seeds0_9.yaml`

Both fix 20,000 simulation seconds, evaluation seeds 0--9 and a 0.8 m safety distance, and cover the
off/hold/rebalance scenarios of S100, S150, M175, M200, M225, L275 and L300.

## 1. Design goals

AMHSTrafficLab lets users register a complete `RoutingStrategy`. A strategy may read the current system
state through the read-only AMHS/OHT/RailPath/Task/WaterLevelArea live objects, and returns one complete
node path.

The public interface does not present routing as a dynamic discrete action space, and offers no next-hop
selection. `SELECT_NEXT_EDGE`, a candidate table, a routing action mask and `WAIT` are all outside the
public API.

## 2. Relationship to the built-in strategies

The current factory's real construction order is:

```python
router = StrategyClass(context, **options)
router.init()
```

The current Q-routing/NQ-routing continue to use the raw graph, env and log callback of the internal
`RoutingContext`; there is no reason to convert them to the public façade. User strategies use
`PublicRoutingContext`, keeping the same lifecycle without leaking kernel objects.

One strategy instance is created per AMHS. A strategy instance may maintain learning state; mutable global
state must not be shared between concurrent runs.

## 3. PublicRoutingContext

| Field | Type | Notes |
|---|---|---|
| `amhs` | `AMHS` | Public read-only live objects |
| `graph` | `ReadOnlyGraph` | Read-only topology façade |
| `env` | `ClockView` | Read-only simulation time, not the SimPy env |
| `routing_targets` | `tuple[str, ...]` | Canonical target IDs |
| `alpha/gamma/tau` | `float` | Current routing parameters |
| `extra` | immutable mapping | User options |
| `py_rng/np_rng` | strategy-owned RNGs | Isolated RNG streams |

The context contains no `current_oht`, no kernel logger, no raw NetworkX and no modifiable routing
table. Vehicle-specific decisions receive the canonical read-only OHT through
`set_decision_context(oht)`; the default hook is a no-op. `ctx.amhs.ohts` remains
available for observing all vehicles.

## 4. RoutingStrategy

The public ABC:

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

    def get_state(self) -> dict: ...
    def set_state(self, state: dict) -> None: ...
    def get_diagnostics(self) -> dict: ...
    def save_checkpoint(self, path) -> None: ...
    def load_checkpoint(self, path) -> None: ...
    def close(self) -> None: ...
```

The base constructor stores `self.ctx`; a subclass that overrides the constructor must call
`super().__init__(ctx, **options)` or store the same context. `update(...)` uses the actual edge-completion parameter
format of the current Q/NQ. `estimate_travel_time(...)` and `estimate_task_time(...)` keep the current
dispatcher routing-cost interface; they must return an exact Python `float`, may use `math.inf` to mark an
unreachable pair, and reject negative values, NaN and `-math.inf`. An algorithm state checkpoint is an
optional strategy hook; it saves no AMHS, EventEngine, resource queue or simulation progress.

`get_best_action` is removed from `RoutingStrategy`; users neither implement nor return a next hop. The
kernel's existing next-hop call sites are changed to call and validate the complete `compute_route` result
first, and the system then extracts the edge it needs internally. The built-in Q/NQ strategies may turn
their per-node selection logic into private helpers, but for the platform they implement only the complete
route contract; their private context and internal learning hooks stay unchanged, with no node-ID
conversion.

## 5. The complete route array

The `compute_route` return value must satisfy:

1. `type(route) is list`;
2. every item satisfies `type(node_id) is str`;
3. the first item is this call's `route_anchor`;
4. the last item is `target_node`;
5. every adjacent ID pair has a RailPath in the current directed graph;
6. the path satisfies the system resource, direction and safety constraints;
7. when start and target are the same it returns `[start_node]`.

The platform performs no numeric/string or alias conversion. Users must return canonical string node IDs
from the map. The platform copies defensively before installing; a user modifying the original list
afterwards does not affect the installed route.

`max_hops` is a search-budget hint. It does not allow a user to return a truncated path, and it is not an
upper bound on the list length of a complete route; the validator will not reject a complete path merely
because it exceeds that hint. The Dijkstra fallback likewise always returns either a complete path or no
path.

## 6. Errors and fallback

| Situation | Handling |
|---|---|
| the strategy raises | record the call context, stop the run and report the error to the user |
| the signature does not match the documentation | registration fails |
| the return value is not a list, or an element is not an exact `str` | report a format error and stop the run |
| a `list[str]` has an invalid anchor, target, adjacency or constraint | record a structured error and call canonical Dijkstra |
| Dijkstra produces a complete valid path | install the fallback and record the reason |
| Dijkstra finds no route | install no partial path; stop the affected OHT safely; raise `NoRouteError` |

## 7. When routing runs

System-required routing runs immediately:

- a new task or target;
- an empty route;
- a route anchor that does not match the actual execution point;
- the current path invalidated by rails, topology or constraints;
- safety recovery requiring the path to be rebuilt.

User conditions only add replanning; they never delay the events above.

### 7.1 Global condition

```python
def condition(amhs) -> bool:
    ...
```

Runs once at each integer simulation second `t=0,1,2,...`. While true, the complete policy runs for every
OHT that has a target and is eligible after the post-Region check, ordered by stable ID.

### 7.2 per-OHT condition

```python
def condition(amhs, oht) -> bool:
    ...
```

Runs once per OHT per integer simulation second, ordered by stable ID; the condition is evaluated before
the target/eligibility filter. Only vehicles that return true and are subsequently eligible replan.

Registration accepts only these two signatures; at runtime `type(result) is bool` is required. While the
condition stays true the complete policy runs every second. A condition may only read public objects;
modifying routes, resource queues or the graph directly raises.

## 8. Same-second order with the Region policy

Region and routing conditions in the same second read the same pre-policy state. The system commits the Region
policy first, then routing re-checks the target, anchor and eligibility and runs the complete policy, and
only then installs the validated complete route.

The planning anchor of a mid-edge OHT:

```python
at_node = (
    oht.path is None or (
        oht.x >= oht.path.length
        and str(oht.current_node) == str(oht.path.end_node.id)
    )
)
anchor = oht.current_node if at_node else oht.path.end_node.id
```

The system never teleports an OHT for replanning, and never modifies the current RailPath, `x` or `v`.

## 9. Minimal example

Use the public imports below. Registration and simulation happen in the same process;
registration is not implicitly propagated to a separate CLI invocation or spawned
worker.

```python
from amhslab import RoutingStrategy, register_routing_strategy, run_simulation

class StaticRoute(RoutingStrategy):
    def __init__(self, ctx, **options):
        super().__init__(ctx, **options)

    def compute_route(self, start_node, target_node, max_hops=None):
        return self.ctx.graph.shortest_path(start_node, target_node)

    def update(
        self, task_id, dest_nodes, from_node, to_node,
        observed_time, next_node=None, agent_id=None,
    ):
        pass

    def estimate_travel_time(self, start_node, end_node):
        return float(self.ctx.graph.shortest_distance(start_node, end_node))

    def estimate_task_time(
        self, current_node, pickup_node, dropoff_node,
    ):
        return self.estimate_travel_time(current_node, pickup_node) + \
            self.estimate_travel_time(pickup_node, dropoff_node)

register_routing_strategy("static-route", StaticRoute, conditions=[lambda amhs: True])
result = run_simulation("experiments/base_config.json", until=120, method="static-route")
print(result.sim_time)
```

All four strategy methods are required and their call signatures are checked at registration.
Duplicate and built-in names are rejected. Options are read from `ctx.extra`; nested
containers are copied and frozen. Estimates are used for dispatch when the profile selects
`routing_dispatch_cost_mode: "router"`. `run_simulation` closes the strategy even if
a run raises, and returns the canonical read-only AMHS view on success.

Missing checkpoint/state-restoration hooks raise `NotImplementedError`; their default
does not silently claim to restore state. Waiting/loading/unloading vehicles are skipped
after conditions are evaluated. Other eligible vehicles plan from their current node or
current rail end, without moving the physical vehicle during route replacement.

## 10. Required tests

- the number of strategy construct/init/close calls;
- neither `RoutingStrategy` nor any kernel call site depends on `get_best_action` any more, and no next-hop appears in the user API;
- the behaviour of the built-in Q/NQ is unchanged by the public context;
- a complete `list[str]` and the absence of a next-hop interface;
- stopping on a format error, semantic fallback, and `NoRouteError`;
- defensive copying and route view generations;
- the signatures, stable order and per-second behaviour of global and per-OHT conditions;
- required routing not waiting for a condition;
- the same-second order of Region and routing, and no feasible overlay.
