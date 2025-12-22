import pytest

from pygha import registry, job
from pygha.transpilers.github import GitHubTranspiler
from pygha.steps import run, checkout, setup_python, shell
from pygha.steps.api import active_job
from pygha.models import Job
from pygha.steps.builtin import RunShellStep, CheckoutStep, UsesStep


def test_run_appends_step_and_returns_it():
    job = Job(name="build")
    with active_job(job):
        step = run("echo hi")

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
        s2 = run("echo step2")
        s3 = run("make build")

    assert job.steps == [s1, s2, s3]
    assert [type(s) for s in job.steps] == [CheckoutStep, RunShellStep, RunShellStep]
    assert s2.command == "echo step2"
    assert s3.command == "make build"


def test_run_raises_if_no_active_job():
    with pytest.raises(RuntimeError, match=r"No active job.*run"):
        run("echo nope")


def test_checkout_raises_if_no_active_job():
    with pytest.raises(RuntimeError, match=r"No active job.*checkout"):
        checkout()


def test_active_job_resets_after_context():
    job = Job(name="test")
    with active_job(job):
        run("echo inside")

    # after exiting the context, calls should fail
    with pytest.raises(RuntimeError, match=r"No active job.*run"):
        run("echo outside")


def test_nested_active_job_isolation():
    outer = Job(name="outer")
    inner = Job(name="inner")

    with active_job(outer):
        s1 = run("echo outer-1")

        # enter nested context for inner job
        with active_job(inner):
            s2 = run("echo inner-1")

        # after inner context, should be back to outer
        s3 = run("echo outer-2")

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


def test_setup_python_basic():
    """Verify basic setup-python step creation."""
    job_obj = Job(name="test-job")
    with active_job(job_obj):
        step = setup_python("3.12")

    assert isinstance(step, UsesStep)
    assert step.action == "actions/setup-python@v5"
    assert step.with_args == {"python-version": "3.12"}
    assert step.name == "Setup Python"
    assert job_obj.steps[0] is step


def test_setup_python_with_cache_and_custom_name():
    """Verify that cache and custom names are handled correctly."""
    job_obj = Job(name="test-job")
    with active_job(job_obj):
        step = setup_python(
            version="3.11", cache="pip", name="Install Python 3.11", action_version="v4"
        )

    expected_args = {"python-version": "3.11", "cache": "pip"}
    assert step.action == "actions/setup-python@v4"
    assert step.with_args == expected_args
    assert step.name == "Install Python 3.11"


def test_setup_python_fails_outside_job():
    """Ensure the helper raises an error if no job is active."""
    with pytest.raises(RuntimeError, match="No active job"):
        setup_python("3.12")


def test_setup_python_golden_yaml(assert_matches_golden):
    """Verify the transpiled YAML output matches the expected format."""
    registry.reset_registry()

    @job(name="build")
    def build_job():
        setup_python("3.12", cache="pip")

    # Get the default 'ci' pipeline
    pipe = registry.get_default()
    yaml_out = GitHubTranspiler(pipe).to_yaml()

    # This will compare the output to a .yml file in your tests/golden/ directory
    assert_matches_golden(yaml_out, "test_setup_python_helper.yml")


def test_shell_deprecation_warning():
    """Verify that calling shell() triggers a DeprecationWarning."""
    job = Job(name="test")

    with active_job(job):
        # This context manager captures warnings of the specified type
        with pytest.warns(FutureWarning, match="Use 'run' instead"):
            shell("echo 'testing deprecation'")
