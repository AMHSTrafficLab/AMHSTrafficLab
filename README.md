# AMHS Simulation Platform

Run OHT transport simulations, inspect them in a GUI, and implement custom routing,
dispatching, and regional-control policies using the installed `amhslab` wheel.

Release **v0.1.2** provides the documentation, experiment inputs, compiled wheel
and 49 learned-policy checkpoints. The runner supports the classical and learned
main matrices (2,730 formal runs), short smoke checks, resume and paper-defined
aggregation. Transfer experiments are excluded. Validation uses short runs; the
complete long matrix has not been rerun.

## Download

Clone or download this repository for documentation and experiment inputs. Download
the matching wheel and, for learned-policy experiments, `learning_checkpoint.tar.gz`
from [Release v0.1.2](https://github.com/AMHSTrafficLab/AMHSTrafficLab/releases/tag/v0.1.2).
The selected artifact identities are recorded in `manifests/release.json`.

| Material | Local location | Purpose |
| --- | --- | --- |
| Platform wheel | `wheelhouse/` | Install the simulation, GUI and public Python API |
| Experiment inputs | `experiments/` | Two experiment matrices, base profile and seven scenes |
| Model checkpoints | `models/routing_final/` | Evaluate 49 trained policies without training |
| Generated results | `outputs/` | Store local runs and verification reports |

## Documentation

| Task | Start here |
| --- | --- |
| Install the platform | [Installation](docs/getting-started/installation.md) |
| Open the GUI or run headlessly | [Quickstart](docs/getting-started/quickstart.md) |
| Understand configuration and maps | [Platform guide](docs/platform/manual.md) |
| Implement a policy | [Public interfaces](docs/api/platform-contract.md) |
| Reproduce the paper experiments | [Reproduction guide](REPRODUCE.md) |
| Diagnose a problem | [Troubleshooting](docs/troubleshooting.md) |
| Check version and validation coverage | [Release information](docs/release/release-notes.md) |

Detailed references: [configuration](docs/platform/configuration.md),
[public fields](docs/api/field-reference.md), [routing](docs/extensions/routing.md),
[dispatch](docs/extensions/dispatch.md), [regional control](docs/extensions/region-control.md),
and [map/region editor](docs/platform/map-editor.md).

The public API is installed with the wheel. No source checkout or editable install
is required. Paper plotting scripts and a full paper-results archive are not supplied.
See `LICENSE`, `NOTICE`, and the third-party license texts in the assembled bundle.

See the [delivery inventory](MATERIALS.md) for the complete upload scope.
Maps, scene configurations and model checkpoints use [CC BY 4.0](LICENSE-DATA.md).
