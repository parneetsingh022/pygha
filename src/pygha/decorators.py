# decorators.py
from typing import TypeVar

from collections.abc import Callable
from .models import Job, Pipeline
from .registry import get_default, register_pipeline
from .steps.api import active_job

R = TypeVar("R")


def job(
    name: str | None = None,
    depends_on: list[str] | None = None,
    pipeline: str | Pipeline | None = None,
    runs_on: str | None = "ubuntu-latest",
) -> Callable[[Callable[[], R]], Callable[[], R]]:
    """Decorator to define a job (expects a no-arg function)."""

    def wrapper(func: Callable[[], R]) -> Callable[[], R]:
        jname = name or func.__name__

        if pipeline is None:
            pipe = get_default()
        elif isinstance(pipeline, Pipeline):
            pipe = pipeline
        elif isinstance(pipeline, str):
            pipe = register_pipeline(pipeline)  # your get-or-create
        else:
            raise TypeError("pipeline must be None, a str, or a Pipeline")

        job_obj = Job(
            name=jname,
            depends_on=set(depends_on or []),
            runner_image=runs_on,
        )

        with active_job(job_obj):
            func()  # user-defined job body (no args)

        pipe.add_job(job_obj)
        return func

    return wrapper
