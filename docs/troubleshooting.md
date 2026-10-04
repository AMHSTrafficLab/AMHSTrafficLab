# Troubleshooting

[Platform README](../README.md)

| Symptom | Check |
| --- | --- |
| Wheel is unsupported | Use the Python version and platform named in the wheel tag |
| `GLIBCXX_3.4.30` is missing | Install/select a compatible system or environment C++ runtime |
| GUI does not open | Check the display and OpenGL environment; imports alone do not test rendering |
| Only a tiny map appears | The synthetic quickstart map is intentionally small; check the selected profile |
| A relative file cannot be found | Run from the platform root and verify the input manifest |
| A checkpoint is missing | Extract all 49 files into `models/routing_final/` and verify their hashes |
| A custom policy is not selected | Register and run it in the same process using the public Python API |

For installation commands see [installation](getting-started/installation.md).
For mismatches, inspect `differences` in the per-case result. For execution failures,
inspect the retained `console.log`. Repeat the same command with `--resume` to reuse
verified cases and retry failed ones. An input/wheel identity mismatch requires
the matching release files or a new output directory, not weakening the checks.
