# Verify main experiment results

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

## Execution checks

The runner verifies the exact expected scene/method/control/seed product, the
requested simulation horizon, process exit status, required outputs and file hashes.
Short smoke runs are stored separately and never counted as formal experiment data.

## Paper aggregation

For a scenario, method and seed, the throughput reference is the maximum of four
CA values: that method's same-seed throughput, Dijkstra's same-seed throughput,
and the across-seed medians of those two methods. CA means regional control `hold`.

DL is true when terminal gridlock is active or throughput is strictly below half
that reference. The wheel's terminal-gridlock field checks that tasks remain open
and no task completed in the final 600 seconds. DE is true when a detector event
was recorded. Both counts use all ten seeds, including collapsed runs.

All other reported means use non-DL runs only. DE without DL remains included.
Percentiles are averaged from per-run percentiles, not recomputed from pooled tasks.
If all seeds collapse, conditional means remain missing. Incomplete runs, missing
CA reference seeds, and smoke data do not produce a completed paper aggregation.

`--matrix all` supplies both learned-method and Dijkstra CA references. Learned-only
execution may complete successfully while its paper statistics remain incomplete.

## Validation boundary

The workflow is checked with short wheel runs and synthetic statistical fixtures.
A full 2,730-run test is not required for this delivery task and has not been run.
The script generates paper-defined statistics but does not compare them against a
separate published-results dataset. It always reports `paper_results_compared: false`.
The optional 49-checkpoint test retains its own exact accepted-record comparison.
