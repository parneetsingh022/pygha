Conditionals
============

GitHub Actions allows you to control when jobs and steps run using the ``if:`` key.
In standard YAML, this often involves writing untyped strings like ``${{ github.event_name == 'push' }}``.

pygha provides a **Python-native** way to express these conditions using decorators, context managers, and type-safe expressions.

Job Conditionals
----------------

To run an entire job only when specific conditions are met, use the ``@run_if`` decorator.
You can stack this with the ``@job`` decorator.

.. code-block:: python

   from pygha import job
   from pygha.decorators import run_if
   from pygha.expr import github

   @job
   @run_if(github.event_name == 'push')
   def deploy():
       # This job only runs on push events
       ...

Step Conditionals
-----------------

To run specific steps conditionally, use the ``when`` context manager.
Any step added inside the block automatically inherits the condition.

.. code-block:: python

   from pygha import job
   from pygha.steps import shell, when, checkout
   from pygha.expr import runner

   @job
   def build():
       checkout()

       # Run specific setup only on Linux
       with when(runner.os == 'Linux'):
           shell("sudo apt-get update")
           shell("sudo apt-get install -y libpq-dev")

       shell("make build")

Nested Conditions
~~~~~~~~~~~~~~~~~

You can nest ``when`` blocks. pygha automatically combines them using the standard GitHub Actions ``&&`` operator.

.. code-block:: python

   from pygha.expr import env

   with when(runner.os == 'Linux'):
       shell("echo Linux")

       with when(env.DEPLOY_TARGET == 'production'):
           # Condition: (runner.os == 'Linux') && (env.DEPLOY_TARGET == 'production')
           shell("./deploy_prod.sh")

Expression Builder
------------------

The ``pygha.expr`` module provides helpers to build expressions without writing raw strings.
It supports standard Python operators for boolean logic.

Context Objects
~~~~~~~~~~~~~~~

* ``github``: Access GitHub context (e.g., ``github.ref``, ``github.actor``).
* ``runner``: Access Runner context (e.g., ``runner.os``, ``runner.arch``).
* ``env``: Access Environment variables (e.g., ``env.MY_VAR``).

Operators
~~~~~~~~~

+----------+--------------------+------------------------------------------+
| Python   | GitHub Actions     | Example                                  |
+==========+====================+==========================================+
| ``==``   | ``==``             | ``github.ref == 'main'``                 |
+----------+--------------------+------------------------------------------+
| ``!=``   | ``!=``             | ``github.actor != 'dependabot'``         |
+----------+--------------------+------------------------------------------+
| ``&``    | ``&&`` (AND)       | ``(cond_a) & (cond_b)``                  |
+----------+--------------------+------------------------------------------+
| ``|``    | ``||`` (OR)        | ``(cond_a) | (cond_b)``                  |
+----------+--------------------+------------------------------------------+
| ``~``    | ``!`` (NOT)        | ``~(github.actor == 'bot')``             |
+----------+--------------------+------------------------------------------+

.. note::
   When using ``&`` and ``|``, you must wrap comparisons in parentheses due to Python's operator precedence rules.

   **Correct:** ``(github.ref == 'main') & (runner.os == 'Linux')``

   **Incorrect:** ``github.ref == 'main' & runner.os == 'Linux'``

Status Check Functions
----------------------

pygha exposes standard status check functions as helpers in ``pygha.expr``.

* ``success()``: Returns true if none of the previous steps have failed (default).
* ``always()``: Causes the step or job to run regardless of the status of previous steps.
* ``failure()``: Returns true if any previous step of a job has failed.

.. code-block:: python

   from pygha.expr import always, failure

   @job
   def cleanup_job():
       # ... do work ...

       # This step runs even if the work failed
       with when(always()):
           shell("docker logout")

       # Send alert only on failure
       with when(failure()):
           shell("./send_slack_alert.sh")
