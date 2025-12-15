import pytest
from pygha import job, pipeline, default_pipeline
from pygha.steps import shell, checkout, echo
from pygha.transpilers.github import GitHubTranspiler
from pygha.registry import register_pipeline, reset_registry, get_default


@pytest.fixture(autouse=True)
def reset_pipeline_registry():
    reset_registry()


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure a clean registry for every test."""
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


def test_bare_job_decorator_registers_job():
    """
    Test that @job (without parentheses) correctly registers the function
    using the function name as the job name.
    """

    # 1. Define a job with the bare decorator
    @job
    def bare_job():
        echo("running bare job")

    # 2. Verify it's in the default pipeline
    pipe = get_default()
    assert "bare_job" in pipe.jobs

    # 3. Verify the job object properties
    job_obj = pipe.jobs["bare_job"]
    assert job_obj.name == "bare_job"
    assert len(job_obj.steps) == 1
    assert job_obj.steps[0].command == 'echo "running bare job"'


def test_bare_job_decorator_transpilation():
    """
    Verify the final YAML output for a bare @job is correct and not empty.
    """

    @job
    def setup_job():
        echo("running setup job")
        shell("python test.py")

    pipe = get_default()
    transpiler = GitHubTranspiler(pipe)
    yaml_out = transpiler.to_yaml()

    # Ensure we don't get "jobs: {}"
    assert "setup_job:" in yaml_out
    assert 'run: echo "running setup job"' in yaml_out
    assert "run: python test.py" in yaml_out


def test_job_decorator_empty_parens_still_works():
    """
    Regression test: Ensure @job() (with empty parentheses) still works.
    """

    @job()
    def explicit_parens():
        echo("I have parents")

    pipe = get_default()
    assert "explicit_parens" in pipe.jobs
    assert pipe.jobs["explicit_parens"].name == "explicit_parens"


def test_job_decorator_args_still_work():
    """
    Regression test: Ensure @job(name='custom') still works.
    """

    @job(name="custom-name")
    def original_function_name():
        pass

    pipe = get_default()
    assert "custom-name" in pipe.jobs
    assert "original_function_name" not in pipe.jobs


def test_job_with_timeout_minutes(assert_matches_golden):
    """
    Test that timeout_minutes is correctly transpiled to timeout-minutes in YAML.
    """
    mypipe = pipeline(
        name="test_job_with_timeout_minutes",
        on_push="main",
    )

    @job(name="build", pipeline=mypipe, timeout_minutes=30)
    def build_job():
        shell("make build")

    @job(name="test", pipeline=mypipe, depends_on=["build"], timeout_minutes=60)
    def test_job():
        shell("pytest")

    out = GitHubTranspiler(mypipe).to_yaml()
    assert_matches_golden(out, "test_job_with_timeout_minutes.yml")


def test_job_without_timeout_minutes_has_no_field():
    """
    Test that jobs without timeout_minutes don't have the field in YAML.
    """
    from ruamel.yaml import YAML

    mypipe = pipeline(
        name="test_no_timeout",
        on_push="main",
    )

    @job(name="build", pipeline=mypipe)
    def build_job():
        shell("make build")

    out = GitHubTranspiler(mypipe).to_yaml()
    yaml = YAML(typ="safe")
    data = yaml.load(out)
    assert "timeout-minutes" not in data["jobs"]["build"]


def test_job_with_invalid_timeout_minutes_raises():
    """
    Test that invalid timeout_minutes values raise ValueError.
    """
    mypipe = pipeline(
        name="test_invalid_timeout",
        on_push="main",
    )

    with pytest.raises(ValueError, match="timeout_minutes must be a positive integer"):
        @job(name="build", pipeline=mypipe, timeout_minutes=0)
        def build_job():
            shell("make build")

    with pytest.raises(ValueError, match="timeout_minutes must be a positive integer"):
        @job(name="test", pipeline=mypipe, timeout_minutes=-10)
        def test_job():
            shell("pytest")
