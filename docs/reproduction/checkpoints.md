# Model checkpoints

[Platform README](../../README.md) · [Reproduction](../../REPRODUCE.md)

Download `learning_checkpoint.tar.gz` from
[Release v0.1.2](https://github.com/AMHSTrafficLab/AMHSTrafficLab/releases/tag/v0.1.2).
The archive contains a `learning_checkpoint/` directory.

Extract into a new target directory to avoid overwriting other model versions:

```bash
mkdir -p models/routing_final
tar -xzf /path/to/learning_checkpoint.tar.gz -C models/routing_final --strip-components=1
sha256sum -c manifests/checkpoints.sha256
```

There are seven files per scene: QLBWR/QECV/BRQ use JSON, NQ/DQN/GDQN use NPZ,
and MAPPO uses PT. Only load checkpoints obtained from the selected release.

| Scene | Filename prefix |
| --- | --- |
| S100 | `s100_2400` |
| S150 | `s150_3120` |
| M175 | `m175_4850` |
| M200 | `m200_5350` |
| M225 | `m225_6100` |
| L275 | `l275_6850` |
| L300 | `l300_7350` |

The weights are external inputs, not embedded in the wheel. Evaluation does not
require rerunning training.
