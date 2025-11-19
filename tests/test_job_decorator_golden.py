import pytest
from pygha import job, pipeline, default_pipeline
from pygha.steps import shell, checkout, echo
from pygha.transpilers.github import GitHubTranspiler
from pygha.registry import register_pipeline, reset_registry


@pytest.fixture(autouse=True)
def reset_pipeline_registry():
    reset_registry()


def test_job_decorator_basic(assert_matches_golden):
    """
    Build a simple two-job pipeline via the real decorator:
      build -> (checkout + two shell runs)
      test  -> needs build, two shell runs
    Compare transpiled YAML to the golden.
    """
    pipeline_name = "test_job_decorator_basic"

    @job(name="build", pipeline=pipeline_name)
    def build_job():
        checkout()
        echo("Building project...")
        shell("make build")

    @job(name="test", depends_on=["build"], pipeline=pipeline_name)
    def test_job():
        echo("Running tests...")
        shell("pytest -v")

    @job(name="with-name", pipeline=pipeline_name)
    def with_name():
        checkout(name="Checkout with name")
        shell("python with_name.py", name="Run Python Script")
        echo("This is echo test with name", name="Echo name test")

    # retrieve the pipeline we decorated into
    pipeline_obj = register_pipeline(pipeline_name)
    # transpile to YAML (ruamel.yaml pretty indent expected)
    out = GitHubTranspiler(pipeline_obj).to_yaml()

    assert_matches_golden(out, "test_job_decorator_basic.yml")


def test_job_decorator_checkout_params(assert_matches_golden):
    """
    Single 'build' job that checks out a specific repo/ref,
    ensuring the 'with:' block is present.
    """

    @job(name="build")  # no pipeline name given, uses default pipeline 'ci'
    def build_job():
        checkout(repository="octocat/hello-world", ref="main")

    out = GitHubTranspiler().to_yaml()

    assert_matches_golden(out, "test_job_decorator_checkout_params.yml")


def test_default_pipeline_creation_with_push_and_pr(assert_matches_golden):
    default_pipeline(on_push=["main", "dev"], on_pull_request=["test1", "test2"])

    @job(name="initial")
    def initial_job():
        echo("Hello world!")

    out = GitHubTranspiler().to_yaml()

    assert_matches_golden(out, "test_default_pipeline_creation_with_push_and_pr.yml")


def test_pipeline_creation_with_push(assert_matches_golden):
    mypipe = pipeline(
        name="test_pipeline_creation_with_push",
        on_push="main",
    )

    @job(name="build", pipeline=mypipe)
    def initial_job():
        shell("pip install pygha")

    out = GitHubTranspiler(mypipe).to_yaml()

    assert_matches_golden(out, "test_pipeline_creation_with_push.yml")


def test_pipeline_creation_with_pr(assert_matches_golden):
    mypipe = pipeline(
        name="test_pipeline_creation_with_pr",
        on_pull_request="main",
    )

    @job(name="build", pipeline=mypipe)
    def initial_job():
        shell("pip install pygha")

    out = GitHubTranspiler(mypipe).to_yaml()

    assert_matches_golden(out, "test_pipeline_creation_with_pr.yml")


def test_pipeline_creation_with_bool(assert_matches_golden):
    mypipe = pipeline(
        name="test_pipeline_creation_with_bool",
        on_push=True,
        on_pull_request=True,
    )

    @job(name="build", pipeline=mypipe)
    def initial_job():
        shell("pip install pygha")

    out = GitHubTranspiler(mypipe).to_yaml()

    assert_matches_golden(out, "test_pipeline_creation_with_bool.yml")


def test_pipeline_creation_with_dict_triggers(assert_matches_golden):
    mypipe = pipeline(
        name="test_pipeline_creation_with_dict_triggers",
        on_push={"branches": ["main"], "paths": ["src/**"]},
        on_pull_request={"branches": ["main"], "paths": ["src/**"]},
    )

    @job(name="build", pipeline=mypipe)
    def build_job():
        shell("pip install pygha")

    out = GitHubTranspiler(mypipe).to_yaml()
    assert_matches_golden(out, "test_pipeline_creation_with_dict_triggers.yml")


def test_pipeline_default_when_no_triggers(assert_matches_golden):
    mypipe = pipeline(name="test_pipeline_default_when_no_triggers")

    @job(name="build", pipeline=mypipe)
    def build_job():
        shell("pip install pygha")

    out = GitHubTranspiler(mypipe).to_yaml()
    assert_matches_golden(out, "test_pipeline_default_when_no_triggers.yml")


def test_pipeline_disable_push_with_empty_list(assert_matches_golden):
    mypipe = pipeline(
        name="test_pipeline_disable_push_with_empty_list",
        on_push=[],  # disables push
        on_pull_request="main",  # keep PR
    )

    @job(name="build", pipeline=mypipe)
    def build_job():
        shell("pip install pygha")

    out = GitHubTranspiler(mypipe).to_yaml()
    assert_matches_golden(out, "test_pipeline_disable_push_with_empty_list.yml")


def test_pipeline_invalid_trigger_type_raises():
    mypipe = pipeline(
        name="test_pipeline_invalid_trigger_type_raises",
        on_push=123,  # invalid
    )

    @job(name="build", pipeline=mypipe)
    def build_job():
        pass

    with pytest.raises(TypeError):
        GitHubTranspiler(mypipe).to_yaml()


def test_pipeline_mixed_dict_and_string(assert_matches_golden):
    mypipe = pipeline(
        name="test_pipeline_mixed_dict_and_string",
        on_push={"branches": ["main"], "paths": ["src/**"]},
        on_pull_request="main",
    )

    @job(name="build", pipeline=mypipe)
    def build_job():
        shell("pip install pygha")

    out = GitHubTranspiler(mypipe).to_yaml()
    assert_matches_golden(out, "test_pipeline_mixed_dict_and_string.yml")
