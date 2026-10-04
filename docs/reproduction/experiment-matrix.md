# Experiment matrix

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

Both matrices use seven scenes, three regional-control modes (`off`, `hold`,
`rebalance`), seeds 0–9 and a requested horizon of 20,000 simulation seconds.

These are the main paper experiment definitions. The implemented checkpoint
precheck selects learned policies, regional control off, seed 0 and 20 seconds:
49 cases. It does not replace the matrices below. Transfer configurations are
excluded from this delivery; see [scope](scope.md).

| Matrix | Routing methods | Cases | Runs |
| --- | --- | ---: | ---: |
| `experiments/routing_classical.yaml` | D, KD, CD, PFD, EDR, CBR | 126 | 1,260 |
| `experiments/routing_learned.yaml` | QLBWR, QECV, BRQ, NQ, DQN, GDQN, MAPPO | 147 | 1,470 |
| Total | 13 methods | 273 | 2,730 |

The scenes are S100, S150, M175, M200, M225, L275 and L300. Their map files are
in `experiments/maps/`; region files are in `experiments/areas/`.
`experiments/base_config.json` supplies shared defaults. Merge the base profile,
selected axis parameters, matrix fixed values and seed in that order. Resolve
checkpoint templates using the selected scene labels.

The packaged matrices preserve experimental parameters. Their paths point into
the delivery directory. Worker count controls resource use, not the experiment
definition; the future runner will allow an override. A short smoke run must be
labelled separately and must not count toward the full experiment completion total.
