Overview
========

pygha treats a workflow as a small graph of :class:`~pygha.models.Job`
objects and keeps them inside a :class:`~pygha.models.Pipeline`.
Each job owns an ordered list of steps and optional dependencies on the
other jobs.  The registry in :mod:`pygha.registry` stores every
pipeline by name so the CLI and transpilers can look them up later.

Minimal pipeline
----------------

The default pipeline is called ``ci``.  The :func:`pygha.registry.default_pipeline`
helper returns it and accepts keyword arguments that map directly to
:class:`pygha.trigger_event.PipelineSettings`.  A practical pipeline
usually consists of at least one ``@job`` function:

.. code-block:: python

   from pygha.decorators import job
   from pygha.steps import shell, checkout

   @job()
   def build():
       checkout()
       shell("pip install -r requirements.txt")
       shell("pytest --maxfail=1")

   if __name__ == "__main__":
       # ensure the pipeline exists and optionally tweak triggers
       from pygha.registry import default_pipeline

       default_pipeline(on_push=["main", "release"], on_pull_request=True)

Pipelines reject duplicate job names and raise on invalid dependency
links.  The underlying topological sort guarantees that the transpiled
workflow follows the declared ``depends_on`` graph.

Configuring Triggers
--------------------

Both ``default_pipeline()`` and ``pipeline()`` accept ``on_push`` and
``on_pull_request`` arguments to control when the workflow runs. These arguments
support several types to handle common GitHub Actions patterns:

* **String**: A single branch name.

  .. code-block:: python

     pipeline("ci", on_push="main")
     # Transpiles to:
     # on:
     #   push:
     #     branches:
     #       - main

* **List of Strings**: A list of branch names. Passing an empty list disables the trigger.

  .. code-block:: python

     pipeline("ci", on_push=["main", "develop"])
     # Transpiles to:
     # on:
     #   push:
     #     branches:
     #       - main
     #       - develop

* **Boolean (True)**: Enables the trigger with GitHub's default filtering (runs on all branches).

  .. code-block:: python

     pipeline("ci", on_pull_request=True)
     # Transpiles to:
     # on:
     #   pull_request:

* **Dictionary**: A raw configuration dictionary for advanced filtering (paths, tags, etc.). This is passed directly to the YAML output.

  .. code-block:: python

     pipeline("ci", on_push={
         "branches": ["main"],
         "paths": ["src/**", "pyproject.toml"]
     })

* **None or False**: Explicitly disables the trigger.

Creating Multiple Pipelines
---------------------------

You can define multiple workflows in a single file (e.g., a CI workflow and a separate Release workflow) using the :func:`pygha.registry.pipeline` function.

To assign a job to a specific pipeline, pass the pipeline object or its name to the ``@job`` decorator:

.. code-block:: python

   from pygha import pipeline, job
   from pygha.steps import shell

   # 1. Define or retrieve the pipelines
   # 'ci' is the default, but we can configure it explicitly here
   ci = pipeline("ci", on_push="main")
   # Create a new pipeline named 'release'
   release = pipeline("release", on_push={"tags": ["v*"]})

   # 2. Assign jobs to the 'ci' pipeline (default if pipeline arg is omitted)
   @job(pipeline=ci)
   def test():
       shell("pytest")

   # 3. Assign jobs to the 'release' pipeline
   @job(pipeline=release)
   def publish():
       shell("twine upload dist/*")

The CLI will generate a separate YAML file for each registered pipeline (e.g., ``ci.yml`` and ``release.yml``).
