<h1 align="center">🧩 PyPipe</h1>

<p align="center">
  <em>A Python-native CI/CD framework for defining, testing, and transpiling pipelines to GitHub Actions.</em>
</p>

---

<p align="center">
  <a href="https://github.com/parneetsingh022/pypipe/actions/workflows/ci.yml">
    <img src="https://github.com/parneetsingh022/pypipe/actions/workflows/ci.yml/badge.svg" alt="CI Status">
  </a>
  <a href="https://codecov.io/gh/parneetsingh022/pypipe">
    <img src="https://codecov.io/gh/parneetsingh022/pypipe/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <img src="https://img.shields.io/badge/lint-Ruff-blue" alt="Lint (Ruff)">
  <img src="https://img.shields.io/badge/type--check-mypy-blue" alt="Type Check (mypy)">
  <img src="https://img.shields.io/badge/security-Bandit-green" alt="Security (Bandit)">
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/parneetsingh022/pypipe.svg" alt="License">
  </a>
</p>

---
## Example: Define a CI Pipeline with `pypipe`

Below is an example of a **Python-defined pipeline** that mirrors what most teams use in production —  
build, lint, test, coverage, and deploy — all orchestrated through `pypipe`.

```python
from pypipe import job, default_pipeline
from pypipe.steps import shell, checkout, upload_artifact, download_artifact

# Define a default pipeline that triggers on pushes to main and dev,
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
    """Build the package and upload the wheel."""
    checkout()
    shell('pip install -U build')
    shell('python -m build')
    upload_artifact('dist/', name='build-artifacts')

@job(name='test', depends_on=['build'])
def test():
    """Run unit tests with coverage."""
    checkout()
    download_artifact('build-artifacts', path='dist/')
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
