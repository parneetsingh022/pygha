Steps API
============

Job bodies run inside the :func:`pygha.steps.active_job` context manager,
which the ``@job`` decorator sets up before executing the user function.
Every helper in :mod:`pygha.steps.api` fetches the active job and
appends a concrete :class:`pygha.models.Step` implementation to it.

Builtin helpers
------------------

``shell(command, name="")``
   Wraps :class:`pygha.steps.builtin.RunShellStep`.  The command is split
   with :mod:`shlex` and executed with ``subprocess.run`` when the
   pipeline is executed locally.
   In GitHub Actions the step becomes a simple ``run:`` block.

``checkout(repository=None, ref=None, name="")``
   Adds a :class:`pygha.steps.builtin.CheckoutStep`.
   When transpiled it emits ``uses: actions/checkout@v4`` with optional
   ``repository`` and ``ref`` inputs.

``uses(action, with_args=None, name="")``
   Adds a :class:`pygha.steps.builtin.UsesStep`. This is the generic way to
   use any GitHub Action from the marketplace.

   The ``with_args`` dictionary is transpiled to the ``with:`` block in YAML.

``echo(message, name="")``
   Convenience wrapper that calls :func:`shell` with
   ``echo "message"`` for quick debugging statements.

Example job
--------------

.. code-block:: python

   from pygha.decorators import job
   from pygha.steps import shell, checkout, echo, uses

   @job(name="quality", depends_on=["build"], runs_on="ubuntu-latest")
   def lint_and_test():
       checkout()

       # Use a marketplace action to setup Python
       uses("actions/setup-python@v5", with_args={"python-version": "3.12"})

       echo("Installing dependencies")
       shell("pip install -r requirements.txt", name="install")
       shell("ruff check", name="lint")
       shell("pytest -q", name="tests")

Custom steps
---------------

To create specialized behavior, subclass :class:`pygha.models.Step` and
implement ``execute`` (for local runs) and ``to_github_dict`` (for
transpilation).
Register the step with a helper function that calls
``job.add_step`` through :func:`active_job`.
This keeps user-facing APIs small while allowing advanced teams to build
higher-level primitives such as ``container`` or ``deploy`` steps.
