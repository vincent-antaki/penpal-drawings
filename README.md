# Penpal: Creative Coding Monorepo

Penpal is a Python-based creative coding environment designed for generating SVGs for pen plotters. It provides a structured workflow to ensure reproducible, version-controlled, and parameterized generative art.

## Directory Structure

- **`core/`**: Shared utilities, drawing abstractions, and math tools (managed via `uv`).
- **`app/`**: Streamlit-based web dashboard to view SVG outputs, parameters, and Git hashes.
- **`tools/`**: Utility scripts, primarily `runner.py`, for executing sketches.
- **`projects/`**: Directory containing individual sketches (e.g., `001_hello_world`).

## Projects Architecture

Each sketch in `projects/` is an independent system utilizing monorepo tooling. 
Every project **MUST** be its own Git repository. The runner relies on Git to snapshot code state for reproducibility.

A typical project contains:
- `main.py`: The entry point defining `run(params, output_path)` to generate an SVG.
- `params.py`: Defines parameter ranges or specific configurations for `main.py`.

## Running Sketches

Execute sketches via `tools/runner.py`, which uses `uv` for environment management.

### Standard Run
Enforces version control and requires a clean Git state. Outputs save to the configured gallery under `<gallery-dir>/<project-id>/svg/<git-hash>/`. Use `--auto-commit` to automatically commit before running.
```bash
python tools/runner.py 001_hello_world
```

### Development / Test Run
Skips Git checks and saves to `<gallery-dir>/<project-id>/test/<timestamp>/`.
```bash
python tools/runner.py 001_hello_world --dev
```

### Custom Parameters
Override `params.py` by providing a JSON string:
```bash
python tools/runner.py 001_hello_world --dev --params '{"seed": 42, "lines": 100}'
```

## Streamlit Dashboard

View generated SVGs, parameters, and Git hashes:
```bash
cd app
./launch.sh
# Or: uv run streamlit run app.py
```
The dashboard allows browsing production runs and testing new parameter configurations interactively.

## SVG Conversion

- [vpype](https://github.com/abey79/vpype) handles post-processing for plotters.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- Git