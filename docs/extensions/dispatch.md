# Dispatching and PRE_ASSIGN

[Platform README](../../README.md)


## 1. The public callable

A user dispatcher uses a strict format:

```python
def dispatch(ohts, tasks, cost_estimator) -> list[DispatchAction]:
    ...
```

- `ohts` and `tasks` are read-only canonical object sequences of the same AMHS;
- `cost_estimator` is a strict `cost_estimator(oht, task) -> float` callable;
- the return value must be an exact Python `list`;
- an empty list means no action this time;
- the only actions are `ASSIGN` and `PRE_ASSIGN`; there is no `NO_OP`, no cancel and no revoke.

The callable signature is checked at registration; the return type, object identity, conflicts and state are
checked at runtime. Users must not write tasks, OHTs, routes or the assignment mapping directly.

`cost_estimator` keeps the third callable parameter of the current dispatcher: an available OHT estimates a
candidate task by the current cost mode, while a busy OHT estimates PRE_ASSIGN as "the remainder of the
current task plus the candidate task". The return value is a non-negative finite Python `float`, or
`math.inf` to mark the pair as infeasible; negative values, NaN and `-math.inf` are errors. `math.inf` must
be treated as a forbidden pair: ASAP skips it and the Hungarian solver masks it, and it must not be replaced
by a large finite number and then assigned; a task with no finite candidate stays pending. The system
provides no extra methods such as `.to_pickup()` or `.after_current()` to users.

## 2. DispatchAction

```python
@dataclass(frozen=True, slots=True)
class DispatchAction:
    kind: DispatchActionKind  # ASSIGN | PRE_ASSIGN
    task: TransportationTask
    oht: OHT
```

An action is immutable. `task` and `oht` must be canonical wrappers of the current AMHS.

## 3. ASSIGN

`ASSIGN` requires:

- the task is `CREATED` and has no assigned or pre-assigned OHT;
- the OHT can currently accept a task;
- the OHT has no current transport task;
- neither the task nor the OHT assignment slot conflicts within the same batch;
- task/vehicle compatibility, the Region intent and the system safety checks pass.

After the commit, the system follows the normal task-start and routing workflow as needed.

## 4. PRE_ASSIGN

`PRE_ASSIGN(task, oht)` reserves a task for an OHT that has not yet finished its current transport task.

Validation:

1. the task is `CREATED`, still pending, and has no assigned or pre-assigned OHT;
2. the OHT is executing a not-yet-finished transport task;
3. the single pre-assignment slot of the OHT is empty;
4. the task and the OHT belong to the same AMHS;
5. the compatibility and Region/Bay intent checks pass;
6. no task or OHT slot conflicts within the mixed batch.

Committing a `PRE_ASSIGN`:

- moves the task to `PRE_ASSIGNED`;
- makes `task.preassigned_oht` and `oht.preassigned_task` consistent in both directions;
- removes the task from the ordinary pending set;
- sets no pickup or start time;
- changes nothing about the OHT's current task, status, target, route, route generation or resource reservation;
- counts the start/end location of that future task once each for the Region/Bay intent under the existing rules, without double counting because both the task and OHT slots are set.

At most one pre-assigned task per OHT, and at most one pre-assigned OHT per task.

## 5. Promotion

After the current task ends successfully, and before the OHT is exposed to the dispatcher as IDLE/available,
the system atomically performs:

```text
task: CREATED -> PRE_ASSIGNED -> IN_PROGRESS
oht.preassigned_task -> oht.current_task
set task.assigned_oht and task.start_time
clear task.preassigned_oht
clear oht.preassigned_task
record task-start event exactly once
create normal target and necessary route
```

Promotion does not go through another round of user dispatch, so no other dispatcher can take the task and
no observer sees the vehicle briefly idle.

If the OHT fails before promotion, or the current task ends on a failure path:

1. clear the task/OHT pre-assignment in both directions;
2. cancel the corresponding Region/Bay future intent;
3. restore the task deterministically to `CREATED` and pending;
4. reuse no invalidated route or reservation;
5. record a structured recovery reason.

## 6. Batch atomicity

All actions returned by one dispatcher call form one batch:

1. freeze the returned list;
2. validate the action types and canonical wrappers;
3. validate the current task/OHT state;
4. build the conflict tables for task slots, current assignment slots and pre-assignment slots;
5. validate compatibility, the Region intent and the safety constraints;
6. commit once, after every action is legal.

If any action is illegal, the whole batch changes no task/OHT mapping, status, target, route, queue or
grant. The commit order of identical legal batches is determined by `(task.id, oht.id, action kind)`.

## 7. ASAP and batch

The configuration key is:

```json
"task_dispatch_mode": "asap"
```

or:

```json
"task_dispatch_mode": "batch"
```

The current Hungarian dispatcher returns matched pairs, and an adapter layer converts each pair to an
`ASSIGN`. The current ASAP calls the assignment path directly; the goal of the implementation is to let
ASAP and batch share the validator/executor described above while keeping the current cost-mode selection
rule, triggering time and stable OHT order: router-based mode uses the strategy's estimated task time,
while static/no-router mode uses the existing static distance rule.

A user dispatcher can be used in either mode, but the public interface never changes the default dispatch
behaviour.

## 8. Example

```python
from math import isfinite

from amhslab import DispatchAction, DispatchActionKind

def lowest_cost(candidates, task, cost_estimator):
    scored = [
        (cost_estimator(oht, task), oht.id, oht)
        for oht in candidates
    ]
    feasible = [row for row in scored if isfinite(row[0])]
    return min(feasible, default=None)

def one_step_lookahead(ohts, tasks, cost_estimator):
    actions = []
    available = [o for o in ohts if o.current_task is None]
    busy_without_slot = [
        o for o in ohts
        if o.current_task is not None and o.preassigned_task is None
    ]

    for task in tasks:
        if task.status != "CREATED":
            continue
        selected = lowest_cost(available, task, cost_estimator)
        if selected is not None:
            _, _, oht = selected
            actions.append(
                DispatchAction(DispatchActionKind.ASSIGN, task, oht)
            )
            available.remove(oht)
            continue

        selected = lowest_cost(busy_without_slot, task, cost_estimator)
        if selected is not None:
            _, _, oht = selected
            actions.append(
                DispatchAction(DispatchActionKind.PRE_ASSIGN, task, oht)
            )
            busy_without_slot.remove(oht)
    return actions
```

## 9. Required tests

- the callable signature and an exact list return;
- when some or all candidates are `math.inf`, neither ASAP nor the Hungarian solver picks a forbidden pair;
- frozen actions and canonical object identity;
- the ASSIGN/PRE_ASSIGN state matrix;
- pre-assign leaving the current task/target/route/reservation untouched;
- the single slot per OHT and per task, and two-way consistency;
- mixed-batch conflicts and the whole batch having no side effects;
- promotion happening before the OHT becomes visible as available;
- failure recovery and intent cleanup;
- behaviour parity between the Hungarian adapter and the default ASAP;
- the Region/Bay future intent counting the start/end location once each, with no double counting from both slots.
