# decorators.py
from typing import Optional, List, Callable, TypeVar
from .models import Job
from .registry import get_default, register_pipeline
from .api import active_job

R = TypeVar("R")

def job(
    name: Optional[str] = None,
    depends_on: Optional[List[str]] = None,
    pipeline: Optional[str] = None,
    runs_on: Optional[str] = "ubuntu-latest",
) -> Callable[[Callable[[], R]], Callable[[], R]]:
    """Decorator to define a job (expects a no-arg function)."""
    def wrapper(func: Callable[[], R]) -> Callable[[], R]:
        jname = name or func.__name__

        pipe = get_default() if pipeline is None else register_pipeline(pipeline)
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
