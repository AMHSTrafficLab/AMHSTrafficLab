# AMHSTrafficLab Map Editor — AMHS Region Catalog tool

[Platform README](../../README.md)


The Map Editor is the **Region management and export tool** for AMHS. It lets you select physical
rails on a read-only map to define Regions, edit or delete existing Regions, and export the result as
an XLSX Region catalog that the simulator can load. The tool **does not modify the map itself**; its
only output is a standalone Region catalog.

## Launch

The map editor is launched through the console entry point:

```bash
amhslab map_editor
```

The editor uses the same dependencies as the simulator plus a GUI toolkit; installing the
distribution brings them in automatically, so no separate dependency step is required. Running from a
source checkout requires those dependencies to be installed first.

## Usage

1. Click, Ctrl+click or drag a box over the physical rails to include in the Region. Nodes are
   available for map browsing and selection handling, but they are not exported as Region members.
2. Fill in the Region ID, water level, quota level and optional rebalance stock, then choose
   **Add current selection to batch**.
3. Choose **Export all regions** to write the batch into the Region catalog.
4. Choose **Load region list...** to inspect, focus, edit or delete Regions from the catalog. Both the
   edit selection and the highlight are expressed as physical rails.

## Region catalog format

The editor's Region membership format consists of these worksheets:

- `Areas`: master data such as Region ID, enabled state, water level, quota level and rebalance
  stock;
- `AreaTracks`: each row associates one `AreaID` with one directed `RailID`.

The runtime loader also accepts `AreaNodes` as an explicit node membership sheet. The Map Editor's
Region list, selection and canvas highlight use `Areas` and `AreaTracks` only, and adding or editing
an Region writes to those two sheets only. When saving an existing catalog, the `AreaNodes` records
of other Regions are left as they are; deleting or renaming an Region clears that Region's related
records from the catalog.

An Region's runtime node set is formed from both endpoints of every `AreaTracks.RailID`. If the
catalog contains `AreaNodes`, the runtime merges those explicit nodes into the set. The full
column definitions and validation rules are in the
[Region Excel Data Dictionary](region-workbook.md).

Data written by the editor must be readable by the same loader used by the GUI and headless runs. A
second save of the same workbook must preserve stable IDs and Region index semantics.

## Safety boundary

The editor modifies map and Region configuration that is not yet running. It does not expose write
access to the graph, routes or resource queues of a running user policy. Runtime admission and
rebalance adjustments can only go through the controlled methods of an `AreaControlPolicy`.

Industrial maps are not part of the public distribution. Examples and tests use synthetic or
explicitly approved fixtures.

## Tests

- synthetic map create/save/reload;
- stable node/rail/Region IDs;
- entry and exit directions;
- invalid membership and dangling references;
- capacity and water-level validation;
- GUI/headless loader parity;
- wheel-only reference-platform launch;
- saved output contains no private paths or industrial identifiers.
