import uuid
from pypipe.decorators import job
from pypipe.api import shell, checkout
from pypipe.transpilers.github import GitHubTranspiler
from pypipe.registry import register_pipeline


def _unique_pipeline_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def test_job_decorator_basic(assert_matches_golden):
    """
    Build a simple two-job pipeline via the real decorator:
      build -> (checkout + two shell runs)
      test  -> needs build, two shell runs
    Compare transpiled YAML to the golden.
    """
    pipeline_name = _unique_pipeline_name("golden-basic")

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

    assert_matches_golden(out, "job_basic.yml")


def test_job_decorator_checkout_params(assert_matches_golden):
    """
    Single 'build' job that checks out a specific repo/ref,
    ensuring the 'with:' block is present.
    """
    pipeline_name = _unique_pipeline_name("golden-checkout")

    @job(name="build", pipeline=pipeline_name)
    def build_job():
        checkout(repository="octocat/hello-world", ref="main")

    pipeline = register_pipeline(pipeline_name)
    out = GitHubTranspiler(pipeline).to_yaml()

    assert_matches_golden(out, "job_checkout.yml")
