# Installation

[Platform README](../../README.md) · [Quickstart](quickstart.md)

The v0.1.2 wheel targets Linux x86_64, CPython 3.11, glibc >= 2.34, and a
libstdc++ providing `GLIBCXX_3.4.30` for DearPyGui. GUI use also needs a display and
OpenGL support. A supported Linux cloud instance can run headless experiments;
Docker is not required if the host environment meets these requirements.

Download the matching wheel from
[Release v0.1.2](https://github.com/AMHSTrafficLab/AMHSTrafficLab/releases/tag/v0.1.2)
into `wheelhouse/`. From the repository root:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --only-binary=:all: -c requirements-runtime.lock wheelhouse/amhslab-*.whl
python -m pip check
amhslab environment_check
```

For matrix reproduction (YAML parsing and learned policies), also install:

```bash
python -m pip install --only-binary=:all: -c requirements-runtime.lock -r requirements-reproduction.lock
python -m pip check
python -c "import yaml, torch; print(yaml.__version__, torch.__version__)"
```

The additional file pins the tested CPU PyTorch build and its dependencies. These
dependencies are installed separately and are not embedded in the platform wheel.

Keep exactly one selected wheel in `wheelhouse/`. The constraint file pins runtime
dependencies; it does not install system libraries. For graphical use also check:

```bash
python -c "import dearpygui.dearpygui; print('GUI runtime import OK')"
```

An import check does not verify window rendering. See
[troubleshooting](../troubleshooting.md) if native-library loading fails.
