# Checkpoint reproduction validation

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

This records the earlier 0.1.1 checkpoint baseline validation. Current candidate
checks are recorded in [candidate validation](candidate-validation.md).

The delivered checkpoint workflow was exercised in an independent Linux
directory containing only delivery materials and downloaded checkpoints. The
simulation was imported from the installed CPython 3.11 compiled wheel.

| Check | Result |
| --- | --- |
| Seven scenes x seven algorithms | 49/49 passed |
| Seed and regional-control mode | Seed 0, area off in every case |
| Horizon | 600 frames / 20 simulation seconds per case |
| Checkpoint hashes and normalized profiles | Matched accepted inputs |
| Routing-call counts and diagnostics | Exact match with previous acceptance records |
| Installed payload | Matched the supplied wheel archive |
| Resume | Reused all 49 completed cases without adding attempts |
| Failure-boundary tests | Six passed |

Validated candidate wheel SHA256:

```text
72d0287086a791ddad81bd0275bd37facf9273f563ce037f42b6b27c58d88328
```

Failure-boundary coverage includes input tampering, path escape, changed resume
identity, damaged exports, source-kernel rejection, numeric checkpoint templates,
timeout recording, changed routing counts and nonfinite simulation time.

The reference was extracted from the earlier accepted checkpoint records; the new
run did not regenerate its expected answers. Wall-clock duration is not compared.
This validates checkpoint test reproduction, not the full paper experiment matrix.
The candidate has not yet been published as the final anonymous release.
