# Execute and resume the main matrices

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

`reproduce_all.py` defaults to plan-only. Use explicit `--mode smoke` or `--mode full`
for execution, and provide the exact installed archive with `--wheel`.
The worker calls the compiled engine shipped in that wheel to obtain the full
KPI and routing statistics. It is version-bound evaluation tooling, not an added
policy interface. It does not import a development checkout or expose internal
admission switches.

`--workers` controls concurrency (default one). Each run has a fresh isolated
Python process, effective profile, output directory and cache paths. Matrix values,
seeds and formal horizons are unchanged. The run loop advances in 600-frame chunks,
as in the existing evaluation runner.

Before execution, the runner checks the exact matrix product, file hashes,
checkpoint hashes when applicable, and installed wheel payload. It records the
Python/dependency environment, hardware information and worker count in the manifest.

`--resume` requires the same plan, mode, inputs, wheel, scripts, environment and
worker count. Completed output hashes are verified before reuse. Failed or damaged
cases run again in fresh attempt directories; previous logs remain available.
Ctrl-C cancels pending work and terminates running workers. Completed cases remain
available for the next resume. Use one runner process per output directory.

Timeouts are optional and measure wall-clock seconds per case. A timeout or program
failure is not a scientific DL outcome. Deadlocks do not automatically stop a run:
formal evaluation continues to its requested horizon.
