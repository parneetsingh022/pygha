pygha documentation
====================

pygha is a lightweight way to describe GitHub Actions workflows with
plain Python functions and decorators.  You declare jobs with the
``@job`` decorator, populate them with high level steps, then hand the
entire pipeline to a transpiler that emits reproducible YAML.

Use these guides to understand the core pieces of the framework and how
they fit together during a typical build.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   overview
   steps
   cli
