# Region Control and Rebalance

[Platform README](../../README.md)


Use the public classes from `amhslab` and pass `area_condition`, `area_policy` and
`rebalance_scheme` together to `run_simulation`. The profile must use
`fixed_water_level_hold`; this loads workbook stocks for custom control without
activating the built-in rebalancer. See the complete implementation pattern in the
[platform manual](../platform/manual.md#9-custom-regional-control).
Keep the condition active when low-water recovery is needed: overrides persist until
cleared. Registrations/callback objects are local to the process running the simulation.

## 1. Model

The uniform runtime Region type is `WaterLevelArea`. An Region carries all of:

- physical membership and occupancy;
- entry admission;
- waiting queue and grants;
- empty-vehicle and stock rebalancing.

Users create, read and modify Regions made of physical rails, their water levels and `rebalance_stock` through
`map_editor`. At runtime the entry/exit edges are derived from the Region's member rails; explicit node
members may come from the `AreaNodes` sheet of an external Region catalog. Runtime objects can be read
directly by a user policy; `controllable` lets a policy decide whether an Region accepts a manual admission
override before committing `set_admission`/`clear_admission_override`. It does not affect
`rebalance_areas` eligibility or `request_rebalance`. Queues, grants, membership and routes can never be
modified directly.

## 2. The per-frame condition

An Region condition is an ordinary registered callable:

```python
def area_condition(amhs) -> bool:
    ...
```

No trigger ABC must be subclassed. The platform checks it every frame, and the return
value must satisfy `type(result) is bool`. While true, the complete policy runs once
that frame: 30 calls per simulation second at the fixed 1/30 s step. False leaves
manual overrides untouched. A policy should schedule and deduplicate periodic
rebalance requests independently; the executable example uses a five-second period.
Routing conditions retain their 1 Hz cadence.

A bad signature fails at registration; a user exception or a non-exact bool fails at runtime. A condition
may read the AMHS, OHTs, tasks, RailPaths, WaterLevelAreas, waiting entries and grants.

## 3. RebalanceCountScheme

```python
class RebalanceCountScheme(ABC):
    @abstractmethod
    def compute(
        self,
        amhs: AMHS,
    ) -> Mapping[WaterLevelArea, int]:
        ...
```

A scheme reads the public live objects directly. `amhs.rebalance_areas` contains the enabled Regions with
`rebalance_stock is not None`, stably ordered by `area_index`.

Return-value rules:

- only a subset of `amhs.rebalance_areas` may be returned;
- an Region that does not appear is treated as 0;
- every key must be a canonical WaterLevelArea wrapper of the same AMHS;
- every value must satisfy `type(value) is int` and may be positive, zero or negative;
- bool, NumPy integers, floats, strings and unknown Regions are rejected;
- a positive number means demand, a negative number means the Region can give vehicles up, and 0 means no net demand.

The built-in water-level scheme may keep using `R = F + Q - I - A`, but the public ABC does not force users
to adopt that formula.

## 4. AreaControlPolicy

```python
class AreaControlPolicy(ABC):
    @abstractmethod
    def execute(
        self,
        amhs: AMHS,
        rebalance_scheme: RebalanceCountScheme,
    ) -> None:
        ...
```

A policy may call the scheme, and may read the complete AMHS state to decide admission. The only legal
write channels are:

```python
amhs.set_admission(area, mode)
amhs.clear_admission_override(area)
amhs.request_rebalance(counts)
```

These methods are available only during the policy stage of `execute`; any other stage raises
`PhaseViolationError`. Calling them only writes a request into the current command buffer. After the policy
returns, the system:

1. freezes the commands;
2. collapses exactly identical commands;
3. rejects conflicting mode or count commands for the same Region;
4. completes command validation and prepares the count mapping;
5. commits once.

A conflict or callback exception prevents the batch from taking effect. Vehicle/route
planning and installation still happen inside the executor during commit; an exception
after commit begins does not guarantee rollback of earlier admission or vehicle changes.

## 5. Admission modes

| Public mode | New entry grants | Effect on existing grants |
|---|---|---|
| `OPEN` | Grants the head of each effective entry queue, with no `high_water - occupancy` quota | Still maintained in same-entry head order |
| `quota` | The total number of far-end grants does not exceed `high_water - occupancy` | Protected grants are kept; the remaining grants rotate between entries in 15-simulation-second time slices |
| `HOLD_NEW_ENTRIES` | None | Keeps the grant of each sorted entry head that is inside the control distance or in `ENTERING`; withdraws every other revocable grant |

The public `AdmissionMode` and `set_admission` accept the three values in the table. The first
`set_admission(area, mode)` installs a persistent manual override; even when that mode equals the automatic
effective mode at that moment, it is still a real state change. Only resubmitting an already existing
identical manual override is idempotent. `clear_admission_override` restores the automatic water-level
logic.

## 6. Automatic water level and immediate execution

The automatic water level maps `occupancy < low_water`, `low_water <= occupancy < high_water` and
`occupancy >= high_water` to `OPEN`, `quota` and `HOLD_NEW_ENTRIES` respectively.
`occupancy` covers the physical members inside the Region and the granted members inside the entry control
distance, and the mode updates immediately within the same `1/30 s` update in which the occupancy changes.

A change to a request, route, occupancy or mode rebalances the queue and grants immediately, but never
fakes an occupancy threshold crossing. The shared-resource rebalance reviews Regions with requests every 3
simulation seconds. All members of an entry are ordered by forward distance and stable request sequence; a
grant that loses its position as the nearest effective head of its entry is withdrawn, and the control
distance only protects a grant that is still the head from water-level revocation.

When `quota` first takes effect, far-end grants are allocated against `C - O`; while
it persists, every far-end grant still outside the control zone is held for 15 simulation seconds. With `F`
the number of such existing grants, only `max(0, C - O - F)` further grants are issued while slots are
free; the first rebalance after expiry swaps one-for-one only with the yet-ungranted heads of other
entries. Without a substitute the original grant and granted time are kept and one more time slice is
granted from that rebalance onwards. This check attaches to the existing reconcile and the 3-second
resource tick. `next_grant_entry_index` indicates the entry the next round considers first, and
`rotation_deadline` indicates the expiry of the grant's current time slice.

`HOLD_NEW_ENTRIES`:

- issues no new grant;
- keeps the grant of each sorted entry head that is inside the control distance or in `ENTERING`;
- withdraws every other revocable grant.

Automatic close:

- keeps the vehicles already inside;
- keeps the `ENTERING` or inside-control-distance grant of each sorted entry head;
- withdraws every other revocable grant and re-enters waiting under the provider rules.

Region right-of-way protection and the near-end grant pre-occupancy share the control distance
`max(0, oht.area_release_distance)`.

## 7. Waiting queue and grants

`WaterLevelArea.waiting_queue` and `WaterLevelArea.grants` are separate read-only views:

- their source is the actual current admission provider;
- waiting is flattened in stable entry order and output by service rank within each entry;
- the complete collection is returned, never truncated;
- a waiting entry exposes only its request ID, OHT, request time and wait time;
- the Region additionally exposes the read-only `next_grant_entry_index`, the zero-based index into `entry_edges` that the next round considers first; it is `None` in other modes or when no entry is available;
- a grant entry exposes its grant ID, OHT, granted time, age, state and read-only `rotation_deadline`; the latter is non-null only for a revocable far-end grant that is rotating;
- when the provider is not ready it raises `ResourceUnavailableError` and never fabricates an empty list;
- users cannot modify the container, members, owner, callbacks or tokens.

## 8. Rebalance execution

The system computes the signed counts together with the active commitments so that no vehicle is dispatched
twice. A vehicle offered for rebalancing must currently be a physical member, idle, and free of transport
tasks, cruising and existing rebalance commitments, and it is selected in stable OHT ID order.

Region pairing and OHT-target matching may keep using Dijkstra/Hungarian. A user scheme only decides the
counts; it never installs a cruise target, route or reservation directly.

## 9. Same-frame order

Within a frame where a routing condition is due:

1. due events;
2. movement;
3. OHT state and occupancy-driven automatic admission;
4. ASAP dispatch;
5. Region and routing conditions computed on the same pre-policy state;
6. the Region policy committed;
7. routing run after re-checking the post-Region state;
8. the route installer installing the validated complete path.

This order lets the Region policy influence the same frame's user routing, while the two conditions never
see different pre-policy states because of evaluation order.

## 10. Example

```python
from amhslab import (
    AdmissionMode,
    AreaControlPolicy,
    RebalanceCountScheme,
)

class StockScheme(RebalanceCountScheme):
    def compute(self, amhs):
        return {
            area: area.rebalance_stock - area.occupancy
            for area in amhs.rebalance_areas
            if area.rebalance_stock != area.occupancy
        }

class CapacityPolicy(AreaControlPolicy):
    def __init__(self):
        self.next_rebalance_time = 0.0

    def execute(self, amhs, rebalance_scheme):
        for area in amhs.areas:
            if not area.controllable:
                continue
            if area.occupancy >= area.high_water:
                amhs.set_admission(
                    area, AdmissionMode.HOLD_NEW_ENTRIES
                )
            elif area.occupancy <= area.low_water:
                amhs.clear_admission_override(area)
        if amhs.sim_time + 1e-9 >= self.next_rebalance_time:
            amhs.request_rebalance(rebalance_scheme.compute(amhs))
            while self.next_rebalance_time <= amhs.sim_time + 1e-9:
                self.next_rebalance_time += 5.0
```

## 11. Required tests

- condition signature, exact bool, per-frame true/false, same-second transitions and zero horizon;
- the scheme reading live wrappers directly;
- count subsets, missing entries as 0, same-AMHS keys, exact ints;
- the policy stage and `PhaseViolationError`;
- command folding, conflicts, and no side effects when validation fails before mutation;
- an occupancy change triggering automatic admission immediately;
- the manual and automatic grant retention rules;
- waiting/grants being complete, separated, and preserving provider container order;
- the three public admission modes, the automatic LOW/MID/HIGH mapping, and rejection of undeclared values;
- `next_grant_entry_index`, `rotation_deadline`, the first rebalance after expiry, and renewal without a substitute;
- the same-frame order of the Region policy and routing;
- behaviour parity between source and wheel.
