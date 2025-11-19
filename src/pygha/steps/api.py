# api.py
from contextlib import contextmanager
from collections.abc import Generator
from contextvars import ContextVar

from .builtin import RunShellStep, CheckoutStep
from pygha.models import Job, Step

_current_job: ContextVar[Job | None] = ContextVar("_current_job", default=None)


@contextmanager
def active_job(job: Job) -> Generator[None, None, None]:
    token = _current_job.set(job)
    try:
        yield
    finally:
        _current_job.reset(token)


def _get_active_job(name: str) -> Job:
    job = _current_job.get()
    if job is None:
        raise RuntimeError(f"No active job. Call '{name}' inside a @job function during build.")
    return job


def shell(command: str, name: str = "") -> Step:
    job = _get_active_job("shell")
    job.add_step(RunShellStep(command=command, name=name))
    return job.steps[-1]


def checkout(repository: str | None = None, ref: str | None = None, name: str = "") -> Step:
    job = _get_active_job("checkout")
    job.add_step(CheckoutStep(repository=repository, ref=ref, name=name))
    return job.steps[-1]


def echo(message: str, name: str = "") -> Step:
    command = f'echo "{message}"'
    return shell(command, name=name)
