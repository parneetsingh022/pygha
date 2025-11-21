# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
