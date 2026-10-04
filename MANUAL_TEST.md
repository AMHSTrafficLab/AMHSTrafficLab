# Release smoke test

[Platform README](README.md) · [Installation](docs/getting-started/installation.md)

Use this checklist with the repository, matching wheel and checkpoint archive from
[Release v0.1.2](https://github.com/AMHSTrafficLab/AMHSTrafficLab/releases/tag/v0.1.2).
A graphical Linux x86_64 session with CPython 3.11 and the runtime requirements in
the installation guide is needed to test the wheel GUI. These commands target the
installed wheel.

## Prepare the release

Clone or download the repository. Put the two release attachments beside it, then
run these commands from the repository root:

```bash
sha256sum -c manifests/SHA256SUMS
mkdir -p wheelhouse models/routing_final
cp /path/to/amhslab-0.1.2-cp311-cp311-manylinux_2_34_x86_64.whl wheelhouse/
tar -xzf /path/to/learning_checkpoint.tar.gz -C models/routing_final --strip-components=1
sha256sum -c manifests/checkpoints.sha256
```

Follow the installation guide to create the environment and install both the wheel
and reproduction dependencies. Then confirm:

```bash
python -c "import importlib.metadata as m, amhslab; print(m.version('amhslab')); print(amhslab.__file__)"
amhslab environment_check
```

Expect version `0.1.2` and an import path in the active environment's
`site-packages`, rather than a source checkout.

## Inspect the full map and GUI

```bash
amhslab config_validate --config experiments/base_config.json
amhslab gui --config experiments/base_config.json
```

- Confirm that the full S150 map loads with 150 vehicles. The separate synthetic
  example is intentionally tiny and should not be used to judge benchmark-map coverage.
- Start, pause and resume; confirm that time and vehicle motion respond.
- Pan and zoom, inspect statistics, then close the window normally.
- Open the map/region editor, inspect the full map and exit:

```bash
amhslab map_editor --map experiments/maps/small_150.xlsx
```

## Check execution and recovery

```bash
python reproduce_all.py --mode plan
python reproduce_all.py --mode smoke --matrix classical --case s100_off__d --wheel wheelhouse/amhslab-0.1.2-cp311-cp311-manylinux_2_34_x86_64.whl --workers 1 --output outputs/manual-smoke
python reproduce_all.py --mode smoke --matrix classical --case s100_off__d --wheel wheelhouse/amhslab-0.1.2-cp311-cp311-manylinux_2_34_x86_64.whl --workers 1 --output outputs/manual-smoke --resume
python reproduce_all.py --mode smoke --matrix learned --case s100_off__gdqn --wheel wheelhouse/amhslab-0.1.2-cp311-cp311-manylinux_2_34_x86_64.whl --workers 1 --output outputs/manual-smoke-learned
```

Expect 2,730 planned main runs and two successful 20-second smoke cases. Resume
should reuse its existing successful attempt. Inspect each output directory's
`reproduction-report.json` and `runs.csv`.
Full-matrix and paper-result comparison flags remain false for this short check.

For broader optional coverage, omit `--case` and `--matrix` and use a new output
directory to run the 13-case smoke. This does not start the full 20,000-second
experiment matrix.

Record the commands, observations and any failure output. Do not substitute a
source-tree run for a wheel test.
