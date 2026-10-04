# Reproduce the main experiments

[Platform README](README.md)

This delivery covers the two main matrices only: 1,260 classical runs and 1,470
learned-policy runs. Each formal run lasts 20,000 simulation seconds, with seeds
0–9 and regional control off, hold or rebalance. Transfer experiments are excluded.

## Prepare

Follow [installation](docs/getting-started/installation.md), then extract the
[49 checkpoints](docs/reproduction/checkpoints.md) for learned-policy evaluation.
Run commands from the extracted platform root. Keep the exact wheel archive used
for installation: the runner verifies installed bytes against it.

## Preview the complete plan

```bash
python reproduce_all.py --mode plan
```

The default is plan-only. It verifies input checksums and the exact matrix product
without starting simulation. Use `--matrix classical` or `--matrix learned` to
preview one matrix (1,260 or 1,470 runs).

## Check that the workflow runs

```bash
python reproduce_all.py --mode smoke   --wheel wheelhouse/EXACT_WHEEL_FILENAME.whl --workers 2
```

Replace the filename with the installed archive. This runs 13 selected seed-0
cases for 20 seconds each, covering all 13 methods, seven scenes and three control
modes. It is not an exhaustive combination test and does not count as formal data.
Use `--case s100_off__d` (repeatable) for a narrower smoke check, or
`--smoke-until SECONDS` to change only the smoke horizon.

## Run the full main matrices when needed

```bash
python reproduce_all.py --mode full   --wheel wheelhouse/EXACT_WHEEL_FILENAME.whl --workers 2
```

This explicit mode launches all 2,730 runs. It was not executed during delivery
smoke validation. Select worker count for the available resources; no runtime
estimate or complete paper-result agreement is implied by the short tests.

To recover an interrupted batch, repeat the same command with `--resume`.
Use `--output PATH` to choose a directory. Defaults separate smoke and full outputs.
An optional `--timeout SECONDS` limits per-run wall time; no timeout is imposed by default.

`--matrix classical` and `--matrix learned` can run separately. Learned-only output
lacks the Dijkstra CA reference required for DL classification, so its paper
aggregation remains incomplete. Use `--matrix all` for a complete statistical input set.

## Outputs and validation

See [execution and recovery](docs/reproduction/run-experiments.md),
[outputs](docs/reproduction/output-format.md), and
[paper statistics](docs/reproduction/verification.md). Completion is checked
separately from paper-result agreement. No reference-table agreement is claimed.
