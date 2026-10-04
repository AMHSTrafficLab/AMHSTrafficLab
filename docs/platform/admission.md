# Region Admission Logic

[Platform README](../../README.md)


> A description of Region admission semantics for platform users. The full type contract for the public
> fields and actions is in `docs/Field_Whitelist.md`.

## 1. Regions, entry edges and the committed water level

An Region is a set of nodes layered over the directed rail graph. Once the configuration resolves the Region
nodes, graph assembly computes its boundaries:

- **Entry edge**: `(node outside the Area, node inside the Area)`;
- **Exit edge**: `(node inside the Area, node outside the Area)`;
- **Intra-Region edge**: an edge whose two endpoints both belong to the Region.

The water level of an Region is its **committed occupancy**, formed by the deduplicated union of the
following members:

| Member | Meaning for the water level |
| --- | --- |
| Physical member | `current_node` lies in the Region node set. |
| Near-end granted member | Holds a grant and has reached the entry control distance, but has not yet crossed into an Region node. |
| Far-end grant | A right of way that may cross the entry; not counted in the water level. |

The pre-entry control distance of an Region is `max(0, oht.area_release_distance)`; Region right-of-way
protection and the near-end grant pre-occupancy share that boundary. An OHT joins the near-end granted
members when it enters the control distance; when it reaches an Region node it becomes a physical member
without being double-counted; the physical water level is released only when it leaves the node set.

Nested or overlapping Regions count and grant independently by their own node sets. When a single boundary
crossing enters several Regions, the OHT must hold the grant of every corresponding Region.

`WaterLevelArea.capacity` is the physical capacity computed from the rails, the OHT length, the safety
distance and the Merge control zone; it is used to validate `high_water`, while runtime admission uses the
committed water level.

## 2. Per-entry queues

Every Region maintains a separate queue per directed entry edge. Queue members are in one of two states,
waiting or granted. Only the sorted head of an entry can hold the entry grant. A grant inside the control
distance is exempt from water-level revocation but does not change the service order within its entry;
when a nearer effective request on the same entry becomes the head, the previous grant is withdrawn and
yields even if it sits inside the control distance. A grant in `ENTERING` is kept by the actual
boundary-crossing lifecycle until it has entered the Region.

### 2.1 Queue ordering

All queue members are ordered by ascending forward distance from the OHT to its registered entry edge;
ties are broken stably by request sequence. Sorting only affects entries that have requests, and is
triggered by:

1. a new request joining the queue;
2. an OHT rerouting to another entry of the same Region, which releases the old request and creates a new one;
3. a semantic reroute of an OHT on the same entry;
4. a head actually entering the Region, or a `release()` call;
5. a physical or near-end occupancy change, or an automatic or manual mode change;
6. the shared-resource rebalance executed every 3 simulation seconds.

The shared-resource rebalance only examines Regions that have requests; it does not run every frame. A
grant that loses its position as the head of its entry after sorting is withdrawn; the control distance
only protects a grant that is still the head from water-level revocation.

### 2.2 Rotation order

When a single event allows several entries to be granted at once, the Region walks the entries in the
stable topological order of `entry_edges`, and each entry grants at most one head per round. The read-only
`next_grant_entry_index` gives the zero-based index that the next round examines first; it is `None` in
other modes or when no entry is available.

## 3. Automatic water-level admission

Let:

- `O = physical + near`: the current committed occupancy;
- `R = low_water`: the quota level;
- `C = high_water`: the hold level.

The automatic water level is divided into three exact bands:

| Band | Condition | Admission behaviour |
| --- | --- | --- |
| Low | `O < R` | Grants the head of every sorted entry. A far-end grant does not consume water level, so that round may issue more than `C - O`. |
| Mid | `R <= O < C` | On first entering MID the protected grants are kept and at most `C - O` far-end grants are issued in rotation order; while MID persists each far-end grant is held for 15 simulation seconds and only rotates one-for-one against other entry heads after expiry. |
| High | `O >= C` | Keeps the protected grant of each sorted entry head, withdraws every other revocable grant, and issues no new entry grant. |

A grant's water-level protection is independent of the band: an OHT inside the control distance, already
pre-occupying the entry control zone, or currently crossing the boundary keeps its grant as long as it is
still the head of its entry. After a grant is withdrawn the request stays in its entry queue, and the next
rebalance determines its service rank.

In automatic MID, let `F` be the number of effective far-end grants still outside the control zone. An
existing far-end grant is not counted in `O`, so when a slot is free only `max(0, C - O - F)` grants can be
issued. When a far-end grant expires it only swaps hands with the head of another not-yet-granted entry; if
there is no substitute it keeps the original grant and granted time, and is renewed for one more time
slice from that rebalance onwards. The read-only `rotation_deadline` gives the expiry moment of the
current time slice; the swap is executed by the first rebalance after expiry, so with only a 3-second
periodic review the actual execution happens later than the threshold but by less than 3 seconds. A grant
inside the control distance, in `ENTERING`, or already physically inside the Region does not take part in
timed revocation.

The `admission_mode` of automatic LOW, MID and HIGH is `OPEN`, `quota` and
`HOLD_NEW_ENTRIES` respectively.

## 4. Manual admission modes

An Region supports three manual override modes:

| Manual mode | Behaviour |
| --- | --- |
| `OPEN` | Ignores the automatic water-level bands and grants the head of every sorted entry. |
| `quota` | Grants far-end heads against the MID quota and rotates between entries in 15-simulation-second time slices. |
| `HOLD_NEW_ENTRIES` | Keeps the protected grant of each sorted entry head, withdraws every other revocable grant, and issues no new entry grant. |

`set_admission()` installs a persistent manual override; `clear_admission_override()` restores automatic
admission against the current committed water level. `controllable` only restricts the runtime control
interface; it does not change automatic water-level admission.

## 5. Grant lifecycle and event-driven reconciliation

1. When an OHT finds its next Region entry edge, a request is created for every Region on that edge.
2. The Region puts the request into the corresponding entry queue, rebalances by current distance, and
   reconciles the head grant within the current event chain.
3. When the granted OHT approaches the control distance it pre-occupies water level.
4. When the OHT's `current_node` enters the Region, the pre-occupancy becomes a physical member and the
   entry grant is released; the entry queue is then rebalanced and the new head reconciled.
5. An OHT calls `release()` before rerouting, cancelling, or leaving the corresponding entry; the Region
   then rebalances that entry and the associated water-level grants.

A new request, a head entering, a head `release()`, a physical or near-end occupancy change, an automatic
mode change, a manual mode change and a semantic reroute all trigger an Region rebalance within the current
event chain. The shared-resource rebalance event adds a distance review every 3 simulation seconds; each
time it only processes Regions that have requests.

When the entry edge on the same Region changes, the OHT releases the old edge record and obtains a new
request ID; a semantic reroute on the same edge rebalances that entry. This way a grant is never reused
across entries.

## 6. Cooperation with Merge admission

A Merge resource still decides the merge right of way from its own directional queues and selector. When
entering a Merge node that belongs to an Region, an OHT must additionally pass the Region gate:

1. an OHT already inside the Region may continue;
2. an outside OHT must hold the Region grant corresponding to that entry edge;
3. when the same edge enters several overlapping Regions, all of those Regions must be satisfied at once;
4. an Region grant-batch change only wakes the Merge queue at the inner end of that Region's entry, and Merge
   re-confirms that the OHT holds the corresponding Region grant when it makes its selection.

Merge's grant flow uses re-entrancy protection: when the Region wakes the same Merge from inside a grant
callback, the nested request is coalesced into the next round after the current selection finishes.

## 7. Public state and verification

Users read Regions through `amhs.areas`, and observe admission state through `waiting_queue`, `grants`,
`next_grant_entry_index`, `queue_version` and `grant_version`. A grant's `rotation_deadline` is non-null
only for a revocable far-end grant under `quota`. `grant_version` increments when a
grant is created, withdrawn, changes state, or when the deadline is updated or cleared; the mere passage
of time does not increment it.

The Region admission tests cover per-entry distance ordering, exclusive ownership of the head,
control-distance protection, rebalancing after entering or `release()`, the mapping between LOW/MID/HIGH
and the public modes, the 15-second rotation and renewal without a substitute, the three manual modes, the
two rotation fields, joint granting across overlapping Regions, rerouting to another entry, the periodic
rebalance, and the coordination of Region and Merge right of way.
