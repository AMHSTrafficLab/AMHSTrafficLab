# Release information

[Platform README](../../README.md)

Version **0.1.2** is the selected platform release. It updates the package
description to match the delivered documentation and reproduction layout.
Simulation behavior and the existing editor source are unchanged. The maps retain
their original field names, values and internal descriptions.

The platform bundle includes English user documentation, two main experiment
matrices, wheel-based reproduction scripts, input checksums and license notices.
Code uses MIT; maps, scene configurations and 49 checkpoints use CC BY 4.0.
The wheel and checkpoints are separate release attachments.

See [candidate validation](candidate-validation.md) for the exact tested wheel and
coverage. Earlier [workflow](main-matrix-validation.md) and
[checkpoint](validation.md) records are retained as historical evidence.
Short tests establish that the workflow runs; a complete 2,730-run reproduction or
agreement with paper result tables has not been evaluated.

The assembled `manifests/release.json`, `manifests/build.json` and checksum files
identify the selected artifacts. Download the wheel and checkpoints from
[Release v0.1.2](https://github.com/AMHSTrafficLab/AMHSTrafficLab/releases/tag/v0.1.2),
and follow the [manual test guide](../../MANUAL_TEST.md) for a short installation
and execution check.
