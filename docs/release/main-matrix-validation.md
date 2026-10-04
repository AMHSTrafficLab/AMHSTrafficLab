# Main-matrix workflow validation

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

This records the earlier 0.1.1 workflow validation. Current candidate checks are
recorded in [candidate validation](candidate-validation.md).

Validation is intentionally limited to planning, short runs and logic tests.
No complete 20,000-second matrix was run for this delivery check.

| Check | Result |
| --- | --- |
| Classical matrix expansion | 1,260 unique scene/method/control/seed combinations |
| Learned matrix expansion | 1,470 unique combinations |
| Formal definitions | 20,000 seconds, seeds 0–9, off/hold/rebalance |
| Actual installed-wheel smoke | 13/13 cases passed, 20 seconds each |
| Smoke coverage | All 13 methods, seven scenes, all three control modes |
| Resume | All 13 results reused; no new attempt directories |
| Targeted logic tests | 12 passed |
| Complete long experiments | Not run |
| Agreement with paper tables | Not evaluated |

The smoke cases were executed outside the source checkout. The installed payload
was verified against candidate SHA256
`72d0287086a791ddad81bd0275bd37facf9273f563ce037f42b6b27c58d88328`.
The worker obtains KPI, routing and diagnostic data from the compiled wheel.
PFD's first initialization took about four wall-clock minutes in this environment;
short simulation time does not imply instant startup.

Tests cover matrix completeness, duplicate seeds, resume identity/output damage,
source-kernel rejection, timeout reporting, checkpoint templates, and DL/DE
statistics. Statistical fixtures check the four-candidate CA reference, the strict
half-throughput threshold, retention of DE-only runs, averaging run-level
percentiles, missing references, and all-collapse cells.

Smoke reports correctly leave full-matrix completion, paper aggregation and
paper-result comparison false. These checks establish that the workflow runs;
they do not establish full scientific reproduction.
