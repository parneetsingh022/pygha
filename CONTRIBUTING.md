## Contributing to PyGHA

First off, thanks for taking the time to contribute! pygha is a Python-native CI/CD framework, and we welcome contributions in the form of bug reports, feature requests, documentation improvements, and code changes.

## Development Setup

### Prerequisites

* Python 3.11+ is required (as specified in pyproject.toml).
* We recommend using a virtual environment for development.

### Installation
1. Clone the repository
    ```bash
    git clone https://github.com/parneetsingh022/pygha.git
    cd pygha
    ```
2. Create and activate a virtual environment
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install development dependencies We use pip with pyproject.toml optional dependencies. This will install the package in editable mode along with testing, linting, and documentation tools.
    ```bash
    pip install -e ".[dev,docs]"
    ```

4. Install Pre-commit Hooks This project uses [pre-commit](https://pre-commit.com/) to enforce code quality before you commit.
    ```bash
    pre-commit install
    ```
    Now, every time you commit, tools like ruff, mypy, and bandit will automatically check your changes.

## Running Tests
We use pytest for testing. The project also utilizes tox to test against multiple Python versions.

```bash
pytest
```

## Documentation
Documentation is built with Sphinx. Source files are located in docs/

To build the documentation locally:
```bash
cd docs
make html
```
The HTML output will be available in `docs/_build/html/index.html`.


## Pull Request Guidelines
1. Fork the repository and create a branch from `main` that reflects your feature name.

2. Add tests for any new features or bug fixes.

3. Update the Changelog: Add a note to `changelog.md` under the `[Unreleased]` section (or create one if it doesn't exist) describing your changes.

4. Ensure tests pass: Run `pytest` locally to ensure functionality; if `pre-commit` is set up, it will automatically detect formatting and other issues.

5. Commit messages: Write clear, descriptive commit messages and submit your Pull Request against the main branch.

## License
By contributing, you agree that your contributions will be licensed under the MIT License defined in the `LICENSE` file.
