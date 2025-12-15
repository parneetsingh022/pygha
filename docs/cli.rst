Command Line Interface
=========================

The :mod:`pygha.cli` module exposes a ``pygha`` console script with
sub-commands for initializing and building pipelines.

Commands
--------

init
~~~~

Scaffolds a new pygha project by creating a sample pipeline file.

.. code-block:: console

   $ pygha init                    # Creates .pipe/ci_pipeline.py
   $ pygha init --src-dir custom   # Creates custom/ci_pipeline.py

The generated ``ci_pipeline.py`` includes a minimal working configuration:

.. code-block:: python

   from pygha import job, default_pipeline
   from pygha.steps import shell, checkout

   default_pipeline(on_push=["main"], on_pull_request=True)

   @job
   def build():
       checkout()
       shell("pip install .")
       shell("pytest")

**Options**

``--src-dir``
   Defaults to ``.pipe``.  The directory where the sample pipeline file
   will be created.

build
~~~~~

Scans a source directory for pipeline files, executes them to populate
the registry, and transpiles each registered pipeline to GitHub Actions YAML.

.. code-block:: console

   $ pygha build --src-dir .pipe --out-dir .github/workflows --clean

**Options**

``--src-dir``
   Defaults to ``.pipe``.  Every file matching ``pipeline_*.py`` or
   ``*_pipeline.py`` in this directory is executed with :mod:`runpy`.

``--out-dir``
   Defaults to ``.github/workflows``.  For each registered pipeline a
   ``<name>.yml`` file is written using :class:`pygha.transpilers.github.GitHubTranspiler`.

``--clean``
   Deletes orphaned YAML files from the output directory unless they
   start with ``# pygha: keep`` within the first ten lines.  This is a
   useful safety valve when rotating pipelines.

**Exit status**

Returns ``0`` even when no pipelines were registered so the command is
safe to run in empty repositories.  Any exception raised while executing
a pipeline file or running the transpiler will propagate to the caller,
giving CI runners immediate feedback.
