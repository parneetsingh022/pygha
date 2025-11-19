import textwrap
import subprocess

from pygha.transpilers.github import GitHubTranspiler
from pygha.steps.builtin import RunShellStep, CheckoutStep
from pygha.models import Job, Pipeline
import pytest

from pygha.steps import shell, checkout, echo, active_job


def _build_pipeline_basic() -> Pipeline:
    # Build job steps (no 'name' passed)
    build_steps = [
        CheckoutStep(),  # no repo/ref so no "with" block
        RunShellStep(command="echo Building project..."),
        RunShellStep(command="make build"),
    ]
    # Test job steps (no 'name' passed)
    test_steps = [
        RunShellStep(command="echo Running tests..."),
        RunShellStep(command="pytest -v"),
    ]

    build = Job(name="build", steps=build_steps)
    test = Job(name="test", steps=test_steps, depends_on={"build"})

    pipe = Pipeline(name="CI")
    pipe.add_job(build)
    pipe.add_job(test)
    return pipe


def _build_pipeline_with_checkout_params() -> Pipeline:
    build_steps = [
        CheckoutStep(repository="octocat/hello-world", ref="main"),
    ]
    build = Job(name="build", steps=build_steps)

    pipe = Pipeline(name="CI")
    pipe.add_job(build)
    return pipe


def test_sorted_unique():
    # Sanity check on helper
    assert GitHubTranspiler._sorted_unique(["b", "a", "b", "c", "a"]) == ["a", "b", "c"]


def test_to_dict_structure_with_real_models():
    pipeline = _build_pipeline_basic()
    tr = GitHubTranspiler(pipeline)
    wf = tr.to_dict()

    # Top level
    assert wf["name"] == "CI"
    assert isinstance(wf["on"], dict)
    assert set(wf["jobs"].keys()) == {"build", "test"}

    # Build job
    build = wf["jobs"]["build"]
    assert build["runs-on"] == "ubuntu-latest"  # default when runner_image is None
    assert "needs" not in build
    # Ensure no 'name' keys sneak into steps
    assert build["steps"] == [
        {"uses": "actions/checkout@v4"},
        {"run": "echo Building project..."},
        {"run": "make build"},
    ]
    assert all("name" not in step for step in build["steps"])

    # Test job
    test = wf["jobs"]["test"]
    assert test["runs-on"] == "ubuntu-latest"
    assert test["needs"] == ["build"]  # sorted/unique list
    assert test["steps"] == [
        {"run": "echo Running tests..."},
        {"run": "pytest -v"},
    ]
    assert all("name" not in step for step in test["steps"])


def test_to_dict_checkout_with_params_adds_with_block():
    pipeline = _build_pipeline_with_checkout_params()
    tr = GitHubTranspiler(pipeline)
    wf = tr.to_dict()

    build = wf["jobs"]["build"]
    assert build["steps"][0] == {
        "uses": "actions/checkout@v4",
        "with": {
            "repository": "octocat/hello-world",
            "ref": "main",
        },
    }


def test_to_yaml_pretty_and_key_order():
    """
    Verifies:
      - 'on:' is unquoted
      - sequences under 'on' and 'steps' are indented (two spaces before '-')
      - 'needs' appears before 'steps' in 'test' job
      - overall YAML matches expected pretty output from ruamel settings
      - no 'name' keys are present in steps
    """
    pipeline = _build_pipeline_basic()
    tr = GitHubTranspiler(pipeline)

    out = tr.to_yaml().replace("\r\n", "\n")

    # 'needs' appears before 'steps' in the 'test' job
    test_block_start = out.find("\n  test:\n")
    assert test_block_start != -1
    needs_idx = out.find("\n    needs:\n", test_block_start)
    steps_idx = out.find("\n    steps:\n", test_block_start)
    assert -1 < needs_idx < steps_idx, "'needs' should come before 'steps' in test job"

    expected = textwrap.dedent(
        """
        name: CI
        on:
          push:
            branches:
              - main
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - uses: actions/checkout@v4
              - run: echo Building project...
              - run: make build
          test:
            runs-on: ubuntu-latest
            needs:
              - build
            steps:
              - run: echo Running tests...
              - run: pytest -v
        """
    ).lstrip()
    assert out.strip() == expected.strip()

    # Bonus: ensure no 'name:' appears anywhere in YAML
    assert "\n      - name:" not in out


######################## Run Shell Step ######################


def test_shell_basic_to_github_dict():
    s = RunShellStep(command="pytest -v")
    assert s.to_github_dict() == {"run": "pytest -v"}


def test_shell_named_to_github_dict():
    s = RunShellStep(command="pytest -v", name="Run tests")
    assert s.to_github_dict() == {"name": "Run tests", "run": "pytest -v"}


def test_shell_execute_runs_subprocess(monkeypatch):
    called = {}

    def fake_run(argv, **kwargs):
        called["argv"] = argv
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    step = RunShellStep(command="echo hello")
    step.execute(context=None)

    assert called["argv"] == ["echo", "hello"]


def test_shell_execute_raises_on_failure(monkeypatch):
    def fake_run(argv, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=argv)

    monkeypatch.setattr(subprocess, "run", fake_run)

    step = RunShellStep(command="exit 1", name="Failing")
    with pytest.raises(subprocess.CalledProcessError):
        step.execute(context=None)


######################## Checkout step ######################
def test_checkout_basic_to_github_dict():
    c = CheckoutStep()
    assert c.to_github_dict() == {"uses": "actions/checkout@v4"}


def test_checkout_named_to_github_dict():
    c = CheckoutStep(name="Checkout repo")
    assert c.to_github_dict() == {"name": "Checkout repo", "uses": "actions/checkout@v4"}


def test_checkout_with_repository():
    c = CheckoutStep(repository="octocat/hello-world")
    assert c.to_github_dict() == {
        "uses": "actions/checkout@v4",
        "with": {"repository": "octocat/hello-world"},
    }


def test_checkout_with_repository_ref_name():
    c = CheckoutStep(repository="octocat/hello-world", ref="dev", name="Checkout dev branch")
    assert c.to_github_dict() == {
        "name": "Checkout dev branch",
        "uses": "actions/checkout@v4",
        "with": {"repository": "octocat/hello-world", "ref": "dev"},
    }


def test_checkout_execute_prints(monkeypatch, capsys):
    c = CheckoutStep(repository="octocat/hello-world")
    c.execute(context=None)
    out = capsys.readouterr().out
    assert "git clone https://github.com/octocat/hello-world.git" in out


############################ echo step ######################
def test_echo_basic(monkeypatch):
    # mock active job
    job = Job(name="build")

    with active_job(job):
        step = echo("Hello world")

    assert step.command == 'echo "Hello world"'
    assert step.name == ""


def test_echo_named(monkeypatch):
    job = Job(name="build")

    with active_job(job):
        step = echo("Hello world", name="Say hello")

    assert step.to_github_dict() == {"name": "Say hello", "run": 'echo "Hello world"'}


def test_api_shell_requires_active_job():
    with pytest.raises(RuntimeError):
        shell("echo hi")


def test_api_checkout_requires_active_job():
    with pytest.raises(RuntimeError):
        checkout()


def test_api_shell_adds_step_and_returns_it():
    job = Job(name="build")
    with active_job(job):
        step = shell("echo hi")
    assert step is job.steps[-1]
    assert step.command == "echo hi"
    # name should be empty string if not provided via API
    assert step.name == ""
    assert step.to_github_dict() == {"run": "echo hi"}


def test_api_shell_with_name_and_empty_name_behavior():
    job = Job(name="build")
    with active_job(job):
        s1 = shell("echo hi", name="Say hi")
        s2 = shell("echo bye", name="")  # empty string
    assert s1.to_github_dict() == {"name": "Say hi", "run": "echo hi"}
    # empty string should be omitted by to_github_dict (falsy)
    assert s2.to_github_dict() == {"run": "echo bye"}


def test_api_checkout_adds_step_and_returns_it_basic():
    job = Job(name="build")
    with active_job(job):
        step = checkout()
    assert step is job.steps[-1]
    assert step.to_github_dict() == {"uses": "actions/checkout@v4"}


def test_api_checkout_with_params_and_name():
    job = Job(name="build")
    with active_job(job):
        step = checkout(repository="octocat/hello-world", ref="main", name="Checkout with name")
    assert step.to_github_dict() == {
        "name": "Checkout with name",
        "uses": "actions/checkout@v4",
        "with": {"repository": "octocat/hello-world", "ref": "main"},
    }
