# api.py
from contextlib import contextmanager
from collections.abc import Generator
from contextvars import ContextVar
from typing import Any

from .builtin import RunShellStep, CheckoutStep, UsesStep
from pygha.models import Job, Step
from pygha.expr import Expression

_current_job: ContextVar[Job | None] = ContextVar("_current_job", default=None)
_condition_stack: ContextVar[list[str]] = ContextVar("_condition_stack", default=[])


def _get_active_condition() -> str | None:
    """Combines all nested conditions with '&&'."""
    stack = _condition_stack.get()
    if not stack:
        return None

    if len(stack) == 1:
        return stack[0]

    # GHA logical AND
    return " && ".join(f"({c})" for c in stack)


@contextmanager
def when(condition: str | Expression) -> Generator[None, None, None]:
    """Context manager to apply 'if' conditions to steps."""
    cond_str = str(condition)
    stack = _condition_stack.get()

    # Push
    token = _condition_stack.set(stack + [cond_str])
    try:
        yield
    finally:
        # Pop is handled by resetting the context var to previous state
        _condition_stack.reset(token)


@contextmanager
def active_job(job: Job) -> Generator[None, None, None]:
    token = _current_job.set(job)
    try:
        yield
    finally:
        _current_job.reset(token)


def _apply_condition(step: Step) -> None:
    """Helper to attach the active condition to a step."""
    cond = _get_active_condition()
    if cond:
        step.if_condition = cond


def _get_active_job(name: str) -> Job:
    job = _current_job.get()
    if job is None:
        raise RuntimeError(f"No active job. Call '{name}' inside a @job function during build.")
    return job


def shell(command: str, name: str = "") -> Step:
    job = _get_active_job("shell")
    step = RunShellStep(command=command, name=name)
    _apply_condition(step)
    job.add_step(step)
    return step


def checkout(repository: str | None = None, ref: str | None = None, name: str = "") -> Step:
    job = _get_active_job("checkout")
    step = CheckoutStep(repository=repository, ref=ref, name=name)
    _apply_condition(step)
    job.add_step(step)
    return step


def echo(message: str, name: str = "") -> Step:
    command = f'echo "{message}"'
    return shell(command, name=name)


def uses(action: str, with_args: dict[str, Any] | None = None, name: str = "") -> Step:
    """
    Adds a generic 'uses' step to the active job.

    Args:
        action: The GitHub action identifier (e.g. 'actions/setup-python@v5').
        with_args: A dictionary of inputs for the action (maps to 'with:').
        name: Optional name for the step.
    """
    job = _get_active_job("uses")
    step = UsesStep(action=action, with_args=with_args, name=name)
    _apply_condition(step)  # <--- Apply condition
    job.add_step(step)
    return step
