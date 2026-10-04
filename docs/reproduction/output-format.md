# Main experiment outputs

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

```text
outputs/<mode>-<matrix>/
  manifest.json
  plan.json
  plan.csv
  results.json
  runs.csv
  classification.csv
  aggregate.csv
  reproduction-report.json
  runs/<run-id>/result.json
  runs/<run-id>/attempt-<id>/profile.json
  runs/<run-id>/attempt-<id>/request.json
  runs/<run-id>/attempt-<id>/console.log
  runs/<run-id>/attempt-<id>/observed.json
```

The manifest records input/wheel/script identities, environment and worker count.
The plan enumerates cases and effective profiles. Each result records its scene,
method, mode, seed, horizon, status (`done` or `failed`), output hashes, and errors.
Observed results include simulated time, frames, KPI statistics, the experiment
report, deadlock events, routing performance and router diagnostics.

`runs.csv` contains raw per-run metrics. `classification.csv` contains DL/DE and
throughput references. `aggregate.csv` contains non-collapse means and seed counts;
missing values are left empty, not converted to zero. Routing latency comes from
the wheel's top-level routing-call timer and remains hardware-dependent.

The report separates `execution_complete`, `all_main_runs_complete`,
`aggregation_complete`, and `paper_results_compared`. A successful smoke run leaves
the last three false. The script does not claim agreement with published tables.
The optional checkpoint test writes its own independent report under `outputs/checkpoints/`.
