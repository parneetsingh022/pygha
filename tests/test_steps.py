import textwrap

from pypipe.transpilers.github import GitHubTranspiler
from pypipe.steps import RunShellStep, CheckoutStep
from pypipe.models import Job, Pipeline


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

    pipe = Pipeline(name='CI')
    pipe.add_job(build)
    pipe.add_job(test)
    return pipe


def _build_pipeline_with_checkout_params() -> Pipeline:
    build_steps = [
        CheckoutStep(repository="octocat/hello-world", ref="main"),
    ]
    build = Job(name="build", steps=build_steps)

    pipe = Pipeline(name='CI')
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
    assert wf["on"] == ["push", "pull_request"]
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

    # 'on:' unquoted and items indented
    assert "\non:\n  - push\n  - pull_request\n" in out

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
          - push
          - pull_request
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
