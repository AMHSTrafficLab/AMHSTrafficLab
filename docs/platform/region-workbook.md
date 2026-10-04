# Region Excel Data Dictionary

[Platform README](../../README.md)


This document describes the workbook structure of an AMHSTrafficLab external Region catalog, the
meaning of each field, and which fields the simulation runtime actually reads.

> Summary: running Region admission needs the `Areas` sheet plus at least one membership sheet,
> either `AreaTracks` or `AreaNodes`. When both membership sheets are present, the runtime merges
> their members. From `Areas`, the Region loader consumes `AreaID`, `Enabled`, `WaterLevel`,
> `ReopenLevel` and the optional `Layer`; with
> `area_control_policy="fixed_water_level_rebalance"` it also needs `RebalanceStock`. From
> `AreaTracks` the runtime consumes only `AreaID` and `RailID`; from `AreaNodes` only `AreaID` and
> `NodeID`. The remaining fields are catalog, visualisation or offline-audit metadata — editing
> them does not directly change admission behaviour.

## 1. Scope and how the catalog is read

A profile references an external catalog through these keys:

```json
{
  "water_level_areas": [],
  "water_level_area_filepath": "<path to the Area catalog workbook>"
}
```

The Region loader turns `Areas` plus the available membership sheet into the `water_level_areas`
configuration; the runtime then rebuilds each Region's nodes, boundaries and physical capacity
against the active map. Therefore:

- An Region's real node set is the union of rail endpoints and explicit nodes: both endpoints of
  every `AreaTracks.RailID` become members, and each `AreaNodes.NodeID` is added as an explicit
  member.
- `AreaCapacity` is an audit value stored in the workbook only. At runtime the physical capacity
  is recomputed from the active map, the OHT length, the safety distance and the merge control
  zone; if `WaterLevel` exceeds the recomputed capacity, the runtime clamps that water level.
- `ReopenLevel` is the quota threshold used after occupancy falls back, and must not exceed
  `WaterLevel`.
- Regions may overlap; each Region counts the OHTs inside its own node set independently.

## 2. The `Areas` sheet

Each row defines one Region. The fields below are the full column set of the reference catalog;
other catalogs of the same kind may carry extra audit sheets, but must not drop runtime-required
columns.

### 2.1 Runtime and visualisation fields

| Field | Type / constraint | Read at runtime | Meaning |
| --- | --- | --- | --- |
| `AreaID` | Non-empty, unique identifier; Excel numbers are normalised to strings | Required | Region primary key; links to `AreaTracks.AreaID`. |
| `BayCode` | Text, e.g. `B02` | No | Catalog/audit label for the Bay the Region belongs to. |
| `Name` | Text | Used by the static map viewer | Human-readable name. |
| `Layer` | Non-negative integer; the loader defaults to `0` when absent | Optional | Nesting level and stable sort key; the runtime sorts by `(Layer, AreaID)`. |
| `SortOrder` | Integer | Used by the static map viewer | Display order within one layer in the viewer; does not affect simulation ordering. |
| `HighlightColor` | `#RRGGBB`, `#RRGGBBAA` or RGB(A) | Used by the static map viewer | Highlight colour for the selected Region. |
| `Enabled` | `true/false`, `yes/no`, `y/n` or `1/0` | Required | Whether this Region is built. When `false`, the row never becomes a runtime Region. |
| `WaterLevel` | Positive integer, at least `1` | Required | Admission hold threshold — the physical occupancy at which the Region stops admitting entries. |
| `ReopenLevel` | Non-negative integer, `≤ WaterLevel` | Required | The Region reopens automatically once physical occupancy falls to or below this value. |
| `RebalanceStock` | Empty, or a non-negative integer | Rebalance policies only | Fixed stock `F`. Blank means admission only, with no rebalance participation; with `fixed_water_level_rebalance` enabled the column must exist and at least one Region should carry a value. |

`WaterLevel`, `ReopenLevel` and `RebalanceStock` reject booleans, decimals, negative values and
infinities. The Region loader also accepts compatible aliases: `Area_ID` / `id`, `Water_Level` /
`water_level`, `Reopen_Level` / `reopen_threshold`, and `rebalance_stock`.

### 2.2 Topology, capacity and spatial audit fields

| Field | Meaning | Runtime effect |
| --- | --- | --- |
| `ProvisionalCap` | Provisional admission cap used when the catalog was generated. | Audit metadata. |
| `WitnessD` | Deadlock/witness vehicle count for this Region. | Audit metadata. |
| `WitnessType` | Witness class, e.g. `pure cycle`. | Audit metadata. |
| `BoundaryCycleID` | Identifier of the cycle that proves or forms the Region boundary; treat it as an opaque ID. | Audit metadata. |
| `AreaCapacity` | Physical capacity produced by the Region capacity formula when the catalog was generated. | Not a runtime manual capacity override; the runtime recomputes it. |
| `PhysicalLengthMM` | Total physical rail length inside the Region, in mm. | Audit metadata. |
| `TrackCount` | Number of `RailID` members of this Region. | Audit metadata. |
| `UniquePhysicalSegmentCount` | Count of distinct physical track sub-segments. | Audit metadata. |
| `XMinMM` / `XMaxMM` | X coordinate bounds of the Region footprint, in mm. | Audit/visualisation metadata. |
| `YMinMM` / `YMaxMM` | Y coordinate bounds of the Region footprint, in mm. | Audit/visualisation metadata. |
| `CoverageBandEndD` | Upper bound `D` of the witness/deadlock scale covered by this Region. | Audit metadata. |
| `Construction` | Description of how the Region's rail set was constructed. | Explanatory text. |
| `SourceAreaIDs` | List of source Region IDs this row was derived from or reuses. | Provenance text. |
| `Notes` | Other generation, capacity or validation remarks. | Explanatory text. |

### 2.3 Water-level rule and enumeration audit fields

| Field | Meaning | Runtime effect |
| --- | --- | --- |
| `CloseLevel` | Hold level used when the catalog was generated. In current catalogs it usually corresponds to `WaterLevel`. | Audit only; admission uses `WaterLevel`. |
| `EffectiveClosedOccupancy` | Minimum occupancy used for accounting or validation while the Region is closed; the usual catalog rule is `ReopenLevel + 1`. | Audit metadata. |
| `BoundaryKappa` | Capacity `κ` of the boundary cycle or resource. | Audit metadata. |
| `EnumerationStatus` | Exactness or validation state of the cycle/deadlock enumeration. | Audit metadata. |
| `CapacityMethod` | Calculation convention or code version used to produce `AreaCapacity`. | Audit metadata. |

For pure-cycle catalogs the usual generation rules are `CloseLevel = κ - 2` and
`ReopenLevel = max(WaterLevel - 4, floor(0.8 × WaterLevel))`. These are catalog generation and
audit rules; they do not replace the loader's per-row validation of `WaterLevel` and
`ReopenLevel`.

## 3. The `AreaTracks` sheet

Each row expresses a membership relation between one Region and one directed rail. `(AreaID,
RailID)` must be unique, and `AreaID` must exist in `Regions`.

| Field | Type / constraint | Read at runtime | Meaning |
| --- | --- | --- | --- |
| `AreaID` | Non-empty ID | Required | Foreign key into `Areas.AreaID`. |
| `RailID` | Non-empty, matching a directed Rail ID in the active map exactly | Required | This rail belongs to the Region; the Region loader rejects unknown rail IDs. |
| `BayCode` | Text | No | Label for consistency auditing against `Areas.BayCode`. |
| `Layer` | Integer | No | Label for consistency auditing against `Areas.Layer`. |
| `StartNode` | Node ID | Not read by the loader; the viewer may use it as a fallback | Rail start node, used for direction and map-change auditing. |
| `EndNode` | Node ID | Not read by the loader; the viewer may use it as a fallback | Rail end node, used for direction and map-change auditing. |
| `RailLengthMM` | Non-negative number, in mm | No | Rail length audit value. |

The same `RailID` may belong to several Regions — that is the normal case for nested or overlapping
Regions. The uniqueness constraint applies only to each `(AreaID, RailID)` pair.

## 4. The `AreaNodes` sheet

Each row expresses a membership relation between one Region and one explicit node. `(AreaID,
NodeID)` must be unique, and `AreaID` must exist in `Regions`. An enabled Region needs at least one
membership row in either `AreaTracks` or `AreaNodes`.

| Field | Type / constraint | Read at runtime | Meaning |
| --- | --- | --- | --- |
| `AreaID` | Non-empty ID | Required | Foreign key into `Areas.AreaID`. |
| `NodeID` | Non-empty, matching a node ID in the active map exactly | Required | Explicit node member of this Region; the runtime validates the node reference. |

`AreaNodes` suits catalogs that need member nodes beyond rail endpoints. The map editor uses the
rail-only membership format: its loading, selection, canvas highlighting and add/edit exports use
`Areas` and `AreaTracks`, and saving never creates or overwrites `AreaNodes`. Deleting or
renaming an Region also clears that Region's related records.

## 5. Other worksheets

Taking `large_300_areas.xlsx` as an example:

| Worksheet | Purpose | Read by the Region loader |
| --- | --- | --- |
| `README` | Catalog scope, provenance, retention rules and compatibility notes. | No |
| `Areas` | Region master sheet. | Yes |
| `AreaTracks` | Region–rail relation sheet. | Yes |
| `AreaNodes` | Region–node explicit membership sheet. | Yes (when present) |
| `BaySummary` / `Audit` / `RevisionLog` / `Computation` / `TargetReview` | Offline audit sheets: per-Bay summary, validation conclusions, revision log, capacity computation process and target review. | No |

Other workbooks of the same kind may also carry `TrimmedMapAudit`, `LayerAudit`,
`CycleSpectrum`, `ResourceWitnesses`, `RuleParameters`, `EnumerationAudit` and
`CrossBayAudit` offline analysis sheets; they do not affect the Region loader's input
contract.

## 6. Pre-edit checklist

1. Never treat `AreaID` or `RailID` as numeric columns; they are identifiers and must stay as-is.
2. To add an Region, add a row to `Areas` and at least one membership relation in `AreaTracks` or
   `AreaNodes`; when exporting from the map editor, membership is written to `AreaTracks`.
3. Check every `RailID` against the active map, paying particular attention to directed IDs and
   the `StartNode` / `EndNode` order.
4. Keep `ReopenLevel ≤ WaterLevel`; fill rebalance stock with a non-negative integer or leave it
   blank.
5. Do not rely on the workbook's `AreaCapacity` as a runtime override; after changing rail
   membership, re-check whether the recomputed runtime capacity still accommodates `WaterLevel`.
6. If you are only revising documentation or audit metadata, avoid touching primary keys,
   thresholds or rail membership in the two runtime sheets.

## 7. Further reading

- [Region control and rebalance](../extensions/region-control.md)
- [Region admission logic](admission.md)
- [Configuration reference](configuration.md)

The internal loader implementation and its region-map plumbing are deliberately out of
scope here: this data dictionary describes the workbook contract, not the private
kernel modules that consume it.
