import pytest
from pypipe import job, pipeline, default_pipeline
from pypipe.steps import shell, checkout
from pypipe.transpilers.github import GitHubTranspiler
from pypipe.registry import register_pipeline, reset_registry


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
    pipeline_name = 'test_job_decorator_basic'

    @job(name="build", pipeline=pipeline_name)
    def build_job():
        checkout()
        shell("echo Building project...")
        shell("make build")

    @job(name="test", depends_on=["build"], pipeline=pipeline_name)
    def test_job():
        shell("echo Running tests...")
        shell("pytest -v")

    # retrieve the pipeline we decorated into
    pipeline = register_pipeline(pipeline_name)
    # transpile to YAML (ruamel.yaml pretty indent expected)
    out = GitHubTranspiler(pipeline).to_yaml()

    assert_matches_golden(out, "test_job_decorator_basic.yml")


def test_job_decorator_checkout_params(assert_matches_golden):
    """
    Single 'build' job that checks out a specific repo/ref,
    ensuring the 'with:' block is present.
    """

    @job(name="build") # no pipeline name given, uses default pipeline 'ci'
    def build_job():
        checkout(repository="octocat/hello-world", ref="main")

    out = GitHubTranspiler().to_yaml()

    assert_matches_golden(out, "test_job_decorator_checkout_params.yml")


def test_default_pipeline_creation_with_push_and_pr(assert_matches_golden):
    default_pipeline(
        on_push=['main', 'dev'],
        on_pull_request=['test1', 'test2']
    )


    @job(name='initial')
    def initial_job():
        shell('echo "Hello world!"')


    out = GitHubTranspiler().to_yaml()

    assert_matches_golden(out, "test_default_pipeline_creation_with_push_and_pr.yml")