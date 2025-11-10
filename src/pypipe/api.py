# api.py
from contextlib import contextmanager
from typing import Generator, Optional
from contextvars import ContextVar

from .steps import RunShellStep, CheckoutStep
from .models import Job, Step

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

def shell(command: str) -> Step:
    job = _get_active_job('shell')
    job.add_step(RunShellStep(command=command))
    return job.steps[-1]

def checkout(repository: Optional[str] = None, ref: Optional[str] = None) -> Step:
    job = _get_active_job('checkout')
    job.add_step(CheckoutStep(repository=repository, ref=ref))
    return job.steps[-1]
