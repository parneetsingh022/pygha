import pytest

from pygha.steps import shell, checkout
from pygha.steps.api import active_job
from pygha.models import Job
from pygha.steps.builtin import RunShellStep, CheckoutStep


def test_shell_appends_step_and_returns_it():
    job = Job(name="build")
    with active_job(job):
        step = shell("echo hi")

    # correct type and placement
    assert isinstance(step, RunShellStep)
    assert job.steps[-1] is step
    # step content
    assert step.command == "echo hi"
    # to_github_dict shape
    assert step.to_github_dict() == {"run": "echo hi"}


def test_checkout_appends_step_and_returns_it_defaults_none():
    job = Job(name="build")
    with active_job(job):
        step = checkout()

    assert isinstance(step, CheckoutStep)
    assert job.steps[-1] is step
    # default arguments should be None
    assert step.repository is None
    assert step.ref is None
    # to_github_dict shape without "with" block
    assert step.to_github_dict() == {"uses": "actions/checkout@v4"}


def test_checkout_appends_step_and_returns_it_with_params():
    job = Job(name="build")
    with active_job(job):
        step = checkout(repository="octocat/hello-world", ref="main")

    assert isinstance(step, CheckoutStep)
    assert job.steps[-1] is step
    assert step.repository == "octocat/hello-world"
    assert step.ref == "main"
    # to_github_dict should include a "with" block when params are provided
    assert step.to_github_dict() == {
        "uses": "actions/checkout@v4",
        "with": {"repository": "octocat/hello-world", "ref": "main"},
    }


def test_steps_accumulate_in_order():
    job = Job(name="build")
    with active_job(job):
        s1 = checkout()
        s2 = shell("echo step2")
        s3 = shell("make build")

    assert job.steps == [s1, s2, s3]
    assert [type(s) for s in job.steps] == [CheckoutStep, RunShellStep, RunShellStep]
    assert s2.command == "echo step2"
    assert s3.command == "make build"


def test_shell_raises_if_no_active_job():
    with pytest.raises(RuntimeError, match=r"No active job.*shell"):
        shell("echo nope")


def test_checkout_raises_if_no_active_job():
    with pytest.raises(RuntimeError, match=r"No active job.*checkout"):
        checkout()


def test_active_job_resets_after_context():
    job = Job(name="test")
    with active_job(job):
        shell("echo inside")

    # after exiting the context, calls should fail
    with pytest.raises(RuntimeError, match=r"No active job.*shell"):
        shell("echo outside")


def test_nested_active_job_isolation():
    outer = Job(name="outer")
    inner = Job(name="inner")

    with active_job(outer):
        s1 = shell("echo outer-1")

        # enter nested context for inner job
        with active_job(inner):
            s2 = shell("echo inner-1")

        # after inner context, should be back to outer
        s3 = shell("echo outer-2")

    # verify placement
    assert [s.command for s in outer.steps if isinstance(s, RunShellStep)] == [
        "echo outer-1",
        "echo outer-2",
    ]
    assert [s.command for s in inner.steps if isinstance(s, RunShellStep)] == [
        "echo inner-1",
    ]

    # sanity checks on types and order
    assert isinstance(s1, RunShellStep)
    assert isinstance(s2, RunShellStep)
    assert isinstance(s3, RunShellStep)
    assert outer.steps[0] is s1
    assert outer.steps[1] is s3
    assert inner.steps[0] is s2
