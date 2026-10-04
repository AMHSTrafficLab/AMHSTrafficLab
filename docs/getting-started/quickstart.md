# Quickstart

[Platform README](../../README.md) · [Installation](installation.md)

Run commands from the repository root after activating the environment. The supplied
base profile opens the complete S150 benchmark map with 150 vehicles.

```bash
amhslab config_validate --config experiments/base_config.json
amhslab headless --config experiments/base_config.json --until 2 --out outputs/quickstart
```

In a desktop session:

```bash
amhslab gui --config experiments/base_config.json
amhslab map_editor --map experiments/maps/small_150.xlsx
```

Use the [reproduction guide](../../REPRODUCE.md) for the seven paper scenes.
The six entrypoints are `environment_check`, `config_validate`, `headless`, `gui`,
`map_editor`, and `benchmark`. The last performs platform microbenchmarks, not
the paper experiment matrix.
