"""
Tests for the core data models in src/pygha/models.py
"""

import pytest
from dataclasses import dataclass
from typing import Any

from pygha.models import Job, Step, Pipeline


# The base 'Step' class is abstract, so we create a simple,
# concrete implementation just for testing.
@dataclass
class _FakeStep(Step):
    """A minimal, concrete Step class for testing."""

    # We just need to implement the abstract methods
    # so we can create an instance of it.

    def execute(self, context: Any) -> None:
        """Mock execute method."""
        print(f"Fake-executing {self.name}")

    def to_github_dict(self) -> dict[str, Any]:
        """Mock to_github_dict method. Converts to GitHub Actions format."""
        return {"run": f"echo '{self.name}'"}


# --- Tests for Job Object ---


def test_job_initialization_defaults():
    """
    Tests that a Job created with only a name has the correct defaults.
    """
    job = Job(name="build")

    assert job.name == "build"
    assert job.steps == []
    assert job.depends_on == set()
    assert job.runner_image is None


def test_job_initialization_with_all_fields():
    """
    Tests that a Job can be created with all fields populated.
    """
    step1 = _FakeStep(name="run-lint")
    dependencies = {"setup"}

    job = Job(name="test", steps=[step1], depends_on=dependencies, runner_image="python:3.11")

    assert job.name == "test"
    assert job.steps == [step1]
    assert job.depends_on == dependencies
    assert job.runner_image == "python:3.11"


def test_job_add_step_method():
    """
    Tests that the add_step() helper method works correctly.
    """
    job = Job(name="deploy")

    # Check that steps list is initially empty
    assert job.steps == []

    # Add a step
    step1 = _FakeStep(name="docker-build")
    job.add_step(step1)

    assert job.steps == [step1]

    # Add a second step
    step2 = _FakeStep(name="docker-push")
    job.add_step(step2)

    # Check that both steps are present in order
    assert job.steps == [step1, step2]


# --- Tests for Pipeline Object ---


def test_pipeline_initialization():
    """Tests that a new Pipeline is created with no jobs."""
    pipe = Pipeline(name="test_pipeline_initialization")
    assert pipe.jobs == {}


def test_pipeline_add_job():
    """Tests that the add_job method correctly adds a job."""
    pipe = Pipeline(name="test_pipeline_add_job")
    job_build = Job(name="build")

    pipe.add_job(job_build)

    assert pipe.jobs == {"build": job_build}


def test_pipeline_add_duplicate_job_raises_error():
    """Tests that adding a job with a duplicate name raises a ValueError."""
    pipe = Pipeline(name="test_pipeline_add_duplicate_job_raises_error")
    job1 = Job(name="build")
    job2 = Job(name="build")  # A different object, but same name

    pipe.add_job(job1)

    with pytest.raises(ValueError, match="A job with the name 'build' already exists."):
        pipe.add_job(job2)


def test_pipeline_get_job_order_simple():
    """Tests a simple, no-dependency list of jobs."""
    pipe = Pipeline(name="test_pipeline_get_job_order_simple")
    job_build = Job(name="build")
    job_test = Job(name="test")

    pipe.add_job(job_build)
    pipe.add_job(job_test)

    order = pipe.get_job_order()

    # Order isn't guaranteed between non-dependent jobs,
    # so we check that both are present.
    assert len(order) == 2
    assert job_build in order
    assert job_test in order


def test_pipeline_get_job_order_linear_dependency():
    """Tests a simple chain (A -> B -> C)."""
    pipe = Pipeline(name="test_pipeline_get_job_order_linear_dependency")
    job_a = Job(name="build")
    job_b = Job(name="test", depends_on={"build"})
    job_c = Job(name="deploy", depends_on={"test"})

    # Add out of order to prove sorting works
    pipe.add_job(job_c)
    pipe.add_job(job_a)
    pipe.add_job(job_b)

    order = pipe.get_job_order()

    assert order == [job_a, job_b, job_c]


def test_pipeline_get_job_order_fan_in_dependency():
    """Tests a "fan-in" graph (A and B -> C)."""
    pipe = Pipeline(name="test_pipeline_get_job_order_fan_in_dependency")
    job_a = Job(name="test-lint")
    job_b = Job(name="test-unit")
    job_c = Job(name="deploy", depends_on={"test-lint", "test-unit"})

    pipe.add_job(job_c)
    pipe.add_job(job_a)
    pipe.add_job(job_b)

    order = pipe.get_job_order()

    # C must be last, but A and B can be in any order
    assert len(order) == 3
    assert order[2] == job_c
    assert job_a in order[:2]
    assert job_b in order[:2]


def test_pipeline_get_job_order_invalid_dependency_raises_error():
    """Tests that a non-existent dependency raises a ValueError."""
    pipe = Pipeline(name="test_pipeline_get_job_order_invalid_dependency_raises_error")
    job_a = Job(name="test", depends_on={"build"})  # "build" does not exist

    pipe.add_job(job_a)

    with pytest.raises(ValueError, match="Job 'test' has an invalid dependency: 'build'"):
        pipe.get_job_order()


def test_pipeline_get_job_order_circular_dependency_raises_error():
    """Tests that a circular dependency (A -> B -> A) raises a ValueError."""
    pipe = Pipeline(name="test_pipeline_get_job_order_circular_dependency_raises_error")
    job_a = Job(name="build", depends_on={"test"})
    job_b = Job(name="test", depends_on={"build"})

    pipe.add_job(job_a)
    pipe.add_job(job_b)

    with pytest.raises(ValueError, match="Circular dependency detected!"):
        pipe.get_job_order()
