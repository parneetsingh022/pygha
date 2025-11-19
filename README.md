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
## Example: Define a CI Pipeline with `pygha`

Below is an example of a **Python-defined pipeline** that mirrors what most teams use in production —  
build, lint, test, coverage, and deploy — all orchestrated through `pygha`.

```python
from pygha import job, default_pipeline
from pygha.steps import shell, checkout

# Define a default pipeline that triggers on main and dev branches,
# and on pull requests to main.
default = default_pipeline(
    on_push=['main', 'dev'],
    on_pull_request='main'
)

@job(name='lint')
def lint():
    """Static analysis and style checks."""
    checkout()
    shell('pip install -U pip ruff mypy')
    shell('ruff check .')
    shell('mypy src')

@job(name='build', depends_on=['lint'])
def build():
    """Build the package."""
    checkout()
    shell('pip install -U build')
    shell('python -m build')

@job(name='test', depends_on=['build'])
def test():
    """Run unit tests with coverage."""
    checkout()
    shell('pip install -e .[dev]')
    shell('pytest --cov=src --cov-report=xml')

@job(name='deploy', depends_on=['test'])
def deploy():
    """Deploy to PyPI when pushing a tagged release."""
    checkout()
    shell('pip install twine')
    shell('if [[ "$GITHUB_REF" == refs/tags/* ]]; then twine upload dist/*; fi')
```

---
