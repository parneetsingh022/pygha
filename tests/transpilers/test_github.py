import textwrap
from pygha.transpilers.github import GitHubTranspiler
from pygha.steps.builtin import RunShellStep, CheckoutStep
from pygha.models import Pipeline


# --- Minimal fakes for Pipeline/Job ---


class FakeJob:
    def __init__(self, name, steps, runner_image=None, depends_on=None):
        self.name = name
        self.steps = steps
        self.runner_image = runner_image
        self.depends_on = depends_on


def _build_pipeline_basic():
    build_steps = [
        CheckoutStep(),  # no repo/ref so no "with" block
        RunShellStep(command="echo Building project..."),
        RunShellStep(command="make build"),
    ]
    test_steps = [
        RunShellStep(command="echo Running tests..."),
        RunShellStep(command="pytest -v"),
    ]
    build = FakeJob(name="build", steps=build_steps, runner_image=None, depends_on=None)
    test = FakeJob(name="test", steps=test_steps, runner_image=None, depends_on=["build"])
    pipeline = Pipeline(name="CI")
    pipeline.add_job(build)
    pipeline.add_job(test)

    return pipeline


def _build_pipeline_with_checkout_params():
    build_steps = [
        CheckoutStep(repository="octocat/hello-world", ref="main"),
    ]
    build = FakeJob(name="build", steps=build_steps)
    pipeline = Pipeline(name="CI")
    pipeline.add_job(build)

    return pipeline


# --- Tests ---


def test_sorted_unique():
    # Sanity check on helper
    assert GitHubTranspiler._sorted_unique(["b", "a", "b", "c", "a"]) == ["a", "b", "c"]


def test_to_dict_structure_with_real_steps():
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
    assert build["steps"] == [
        {"uses": "actions/checkout@v4"},
        {"run": "echo Building project..."},
        {"run": "make build"},
    ]

    # Test job
    test = wf["jobs"]["test"]
    assert test["runs-on"] == "ubuntu-latest"
    assert test["needs"] == ["build"]  # sorted / unique list
    assert test["steps"] == [
        {"run": "echo Running tests..."},
        {"run": "pytest -v"},
    ]


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
    """
    pipeline = _build_pipeline_basic()
    tr = GitHubTranspiler(pipeline)

    out = tr.to_yaml().replace("\r\n", "\n")

    # 'needs' appears before 'steps' in 'test' job block
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
