# Delivery materials

[Platform README](README.md)

## Repository

- English README, installation and platform guides, public interface references,
  policy-writing guides, reproduction instructions and validation summaries.
- Two formal main-matrix definitions, their shared base profile, seven maps and
  seven matching region workbooks.
- `reproduce_all.py` and its main-matrix execution and statistics support modules.
- Runtime and reproduction dependency pins, licenses and notices.
- Input/checkpoint checksums and a concrete public file manifest.

## Separate release attachments

- The selected CPython 3.11 Linux x86_64 wheel.
- `learning_checkpoint.tar.gz`: 49 model files and their license notices.

The wheel and weights are not duplicated in Git history.
Download the wheel into `wheelhouse/` and extract the weights as described in
the [checkpoint guide](docs/reproduction/checkpoints.md).

## Excluded

Private simulation source and Git history, internal plans, development logs,
paper PDFs, plotting scripts, full paper-result archives and transfer experiments
are not part of this delivery. Standalone running/extension examples, synthetic
example maps/configurations, checkpoint short-test reference data and the associated
reference-comparison precheck are also excluded. The routing and regional-policy
writing guides remain included. The 49 actual model checkpoints remain release
attachments. Users generate experiment outputs locally.

Code is MIT-licensed. Maps, scene configurations and weights use CC BY 4.0;
see [data licensing](LICENSE-DATA.md). Third-party notices are preserved.
