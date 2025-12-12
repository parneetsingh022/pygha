# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-12-11

### Added
- **Matrix Strategy**: Added support for defining build matrices in jobs via the `matrix` argument in the `@job` decorator. This allows for dynamic job generation (e.g., testing across multiple Python versions or operating systems).
- **Fail Fast**: Added `fail_fast` argument to `@job` to control the `strategy: fail-fast` behavior in generated workflows.
- **Generic Uses Step**: Added `uses()` helper in `pygha.steps` to allow using any GitHub Action from the marketplace (e.g., `uses("actions/setup-python@v5")`). This supports both `with` arguments and custom step names.
- **Conditional Logic**: Introduced Python-native conditional logic for Jobs and Steps.
  - Added `@run_if` decorator for Job-level conditions (e.g., `@run_if(github.event_name == 'push')`).
  - Added `when` context manager for Step-level conditions (e.g., `with when(runner.os == 'Linux'):`).
  - Added `pygha.expr` module to build type-safe expressions using Python operators (e.g., `(github.ref == 'main') & (runner.os == 'Linux')`).
- **Condition Helpers**: Added `always()`, `success()`, and `failure()` helpers for status checks.
- **Context Objects**: Added `github`, `runner`, and `env` context helpers to `pygha.expr` for easy auto-completion.

### Changed
- **Test Infrastructure**: Refactored `tests/transpilers/test_github.py` to use real `Job` models instead of the `FakeJob` class, ensuring tests stay synchronized with the core model definitions.
- **Transpiler**: Updated `GitHubTranspiler` to correctly render `if:` keys for Jobs and Steps.
- **YAML Formatting**: Increased default line width in YAML output to 4096 characters to prevent wrapping of long conditional expressions.
- **Step Models**: Updated `Job` and `Step` models to include an optional `if_condition` field.

## [0.1.0] - 2025-11-18

### Added
- **Core Framework**: Initial release of `pygha`, a Python-native CI/CD framework for defining pipelines.
- **Pipeline Models**: Introduced `Pipeline`, `Job`, and `Step` classes to structurally define workflows.
- **Decorators**: Added `@job` decorator to register Python functions as CI jobs.
- **GitHub Actions Transpiler**: Implemented `GitHubTranspiler` to convert Python pipeline objects into valid GitHub Actions YAML.
- **CLI**: Added `pygha build` command to scan, execute, and transpile pipelines from the `.pipe` directory.
- **Steps API**:
  - `shell`: Execute shell commands (transpiles to `run:`).
  - `checkout`: Wrapper for `actions/checkout@v4`.
  - `echo`: Convenience wrapper for printing messages.
- **Configuration**:
  - Support for defining triggers (`on_push`, `on_pull_request`) with strings, lists, or dictionaries.
  - `default_pipeline()` helper for quick setup of standard CI workflows.
