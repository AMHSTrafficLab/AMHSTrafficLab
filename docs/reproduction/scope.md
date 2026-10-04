# Reproduction scope

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

| Matrix | Methods | Scenes | Control modes | Seeds | Runs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Classical | 6 | 7 | 3 | 10 | 1,260 |
| Learned | 7 | 7 | 3 | 10 | 1,470 |
| Total | 13 | 7 | 3 | 10 | 2,730 |

Every formal run has a 20,000-second horizon. Control modes are off, hold and
rebalance (C0, CA and CAR); seeds are 0–9. Transfer evaluation is not included.
The 49 checkpoints are inputs reused across control settings and seeds.

The workflow offers plan-only, short smoke and full execution modes. Delivery
validation covers short execution and logic tests, not a complete 2,730-run rerun.
The separate 49-case checkpoint comparison is an optional precheck.

Paper aggregation follows D.4.2–D.4.3: count DL and DE over all seeds, and average
other run-level statistics over non-DL runs. See [verification](verification.md).
