<div align="center">
  <a href="https://github.com/parneetsingh022/pygha"><img alt="logo_pygha_dark" width="300px" src="https://github.com/user-attachments/assets/c2801ef9-4224-4cff-8f29-1e4464833a3a" /></a>
</div>


<p align="center">
  <em>A Python-native CI/CD framework for defining, testing, and transpiling pipelines to GitHub Actions.</em>
</p>
<p align="center">
  <strong><a href="https://pygha.readthedocs.io/">Read the Full Documentation</a></strong>
</p>

---

<p align="center">
  <a href="https://pypi.org/project/pygha/">
    <img src="https://img.shields.io/pypi/v/pygha?color=blue" alt="PyPI">
  </a>
  <a href="https://anaconda.org/psidhu22/pygha">
    <img src="https://img.shields.io/conda/vn/psidhu22/pygha?color=green&label=anaconda" alt="Conda Version">
  </a>
  <a href="https://pypi.org/project/pygha/">
    <img src="https://img.shields.io/pypi/pyversions/pygha" alt="Python Versions">
  </a>
  <a href="https://github.com/parneetsingh022/pygha/actions/workflows/ci.yml">
    <img src="https://github.com/parneetsingh022/pygha/actions/workflows/ci.yml/badge.svg" alt="CI Status">
  </a>
  <a href="https://pygha.readthedocs.io/">
    <img src="https://img.shields.io/readthedocs/pygha" alt="Documentation Status">
  </a>
  <a href="https://codecov.io/gh/parneetsingh022/pygha">
    <img src="https://codecov.io/gh/parneetsingh022/pygha/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <img src="https://img.shields.io/badge/lint-Ruff-blue" alt="Lint (Ruff)">
  <img src="https://img.shields.io/badge/type--check-mypy-blue" alt="Type Check (mypy)">
  <img src="https://img.shields.io/badge/security-Bandit-green" alt="Security (Bandit)">
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/parneetsingh022/pygha.svg" alt="License">
  </a>
</p>

---

## Installation

### PyPI
You can install `pygha` via pip:
```bash
pip install pygha
```

### Conda
You can install pygha from the psidhu22 channel:
```bash
conda install -c psidhu22 pygha
```


## Example: Define a CI Pipeline with `pygha`

Below is an example of a **Python-defined pipeline** that mirrors what most teams use in production —
build, lint, test, coverage, and deploy — all orchestrated through `pygha`.

```python
from pygha import job, default_pipeline
from pygha.steps import shell, checkout, uses

# Configure the default pipeline to run on main push and PRs
default_pipeline(on_push=["main"], on_pull_request=True)

@job(
    name="test",
    matrix={"python": ["3.11", "3.12", "3.13"]},
)
def test_matrix():
    """Run tests across multiple Python versions."""
    checkout()

    # Use the matrix variable in your step arguments
    uses(
        "actions/setup-python@v5",
        with_args={"python-version": "${{ matrix.python }}"}
    )

    shell("pip install .[dev]")
    shell("pytest")

@job(name="deploy", depends_on=["test"])
def deploy():
    """Build and publish if tests pass."""
    checkout()
    uses("actions/setup-python@v5", with_args={"python-version": "3.11"})

    shell("pip install build twine")
    shell("python -m build")
    shell("twine check dist/*")
```

## Advanced: Conditional Logic
`pygha` allows you to write conditional workflows using Python syntax instead of raw YAML strings.

### Job-Level Conditions
Use the `@run_if` decorator to skip entire jobs based on context.
```python
from pygha.decorators import run_if
from pygha.expr import github

@job(name="nightly-scan")
@run_if(github.event_name == "schedule")
def security_scan():
    """Only runs on scheduled events."""
    ...
```

### Step-Level Conditions
Use the `when` context manager to group steps that should only run under certain conditions. Nested conditions are automatically `AND`-ed together.

```python
from pygha.steps import when
from pygha.expr import runner, always, failure

@job
def conditional_steps():
    # Simple check
    with when(runner.os == 'Linux'):
        shell("sudo apt-get update")

    # Status check helper (runs even if previous steps failed)
    with when(always()):
        shell("echo 'Cleanup...'")

    # Nested check: (failure()) AND (runner.os == 'Linux')
    with when(failure()):
        with when(runner.os == 'Linux'):
            shell("echo 'Linux build failed!'")
```
