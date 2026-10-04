# Version 0.1.2 validation

[Platform README](../../README.md) · [Manual testing](../../MANUAL_TEST.md)

Selected wheel: `amhslab-0.1.2-cp311-cp311-manylinux_2_34_x86_64.whl`.

SHA256:

```text
9f813d56636149fb4625f30e9e2876d7f21e9b0952f3f899f7fa8341506d5af4
```

## Checks on the selected archive

| Check | Result |
| --- | --- |
| Wheel contents and leakage scan | Passed |
| Fresh environment install and dependency check | Passed |
| Six CLI entrypoints | Passed |
| Public contract tests | 224 passed |
| Custom routing and regional-control examples | Passed |
| Actual GUI on full S150 map | 150 vehicles, 3,334 nodes, 3,419 rails; run, pause, resume and close passed |
| Actual map/region editor | Full S150 map rendered; closed normally |
| Final wheel short execution | Dijkstra and GDQN, 20 seconds each, passed |
| Resume of those two cases | Both reused; no additional attempts |
| Main experiment plan | 2,730 runs; ten seeds; 20,000 seconds |
| Complete long experiments | Not run |
| Agreement with paper tables | Not evaluated |

GUI checks rendered real windows on a Linux test display. Manual interaction and
visual review remain the final acceptance step.

## Broader short-run evidence

The preceding 0.1.2 candidate, SHA256
`99263826665c090ebe5173c2386d370d6390bcfc9365aadc6cb59a36c397da99`,
passed all 13 representative main-matrix smoke cases and all 49 checkpoint cases.
Checkpoint routing counts and diagnostics matched the unchanged 0.1.1 reference
exactly; simulated time uses a tolerance of 1e-7 seconds. All 49 completed cases
were reused successfully by resume.

The selected archive restores the existing editor comments and docstrings. All
85 compiled extensions, public API modules and runtime configurations are byte
identical to that preceding candidate. The three editor modules have identical
executable syntax after excluding docstrings. The broader 13/49 batches were not
repeated after this comment-only correction; the selected archive received the
direct checks above.

The reference record retains the original baseline wheel identity. The checkpoint
runner verifies the installed bytes against the wheel selected in the delivery
manifest and compares against the unchanged reference results. It does not replace
expected results with newly observed ones.

Maps retain their original cells and formulas; only identifying document metadata
is removed from delivery copies. All 49 checkpoint files retain their original
bytes. Internal comments and map descriptions are not subject to user-facing
language cleanup. The selected archive is published with Release v0.1.2.
