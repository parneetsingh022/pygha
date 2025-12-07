import pytest
from pygha.registry import register_pipeline
from pygha import job
from pygha.steps import uses, active_job
from pygha.steps.builtin import UsesStep
from pygha.models import Job
from pygha.transpilers.github import GitHubTranspiler


def test_uses_basic_api():
    """Verify 'uses' adds the correct step object with defaults."""
    job_obj = Job(name="setup")
    with active_job(job_obj):
        step = uses("actions/checkout@v4")

    assert isinstance(step, UsesStep)
    assert job_obj.steps[-1] is step
    assert step.action == "actions/checkout@v4"
    assert step.with_args is None
    # Verify transpilation dictionary output
    assert step.to_github_dict() == {"uses": "actions/checkout@v4"}


def test_uses_full_api():
    """Verify 'uses' handles names and arguments correctly."""
    job_obj = Job(name="setup")
    with active_job(job_obj):
        step = uses(
            "actions/setup-node@v3",
            with_args={"node-version": "18", "cache": "npm"},
            name="Install Node",
        )

    expected = {
        "name": "Install Node",
        "uses": "actions/setup-node@v3",
        "with": {"node-version": "18", "cache": "npm"},
    }
    assert step.to_github_dict() == expected


def test_uses_fails_without_active_job():
    """Ensure it crashes cleanly if used outside a @job function."""
    with pytest.raises(RuntimeError, match=r"No active job.*uses"):
        uses("actions/checkout@v4")


def test_uses_local_execution(capsys):
    """Verify the step prints correctly when running locally (not transpiling)."""
    step = UsesStep(action="my-action@v1", with_args={"key": "value"})
    step.execute(context=None)

    out = capsys.readouterr().out
    assert "Using action: my-action@v1" in out
    assert "With args: {'key': 'value'}" in out


def test_uses_golden_yaml_generation(assert_matches_golden):
    """
    Defines a real pipeline with multiple 'uses' scenarios and
    compares the final YAML against a golden file.
    """
    pipeline_name = "test_uses_golden"

    @job(name="deploy", pipeline=pipeline_name)
    def deploy_job():
        # Case 1: Simple action
        uses("actions/checkout@v4")

        # Case 2: Action with name and inputs
        uses("actions/setup-python@v5", with_args={"python-version": "3.12"}, name="Setup Python")

        # Case 3: Action with secrets (ensures variable passing works)
        uses(
            "aws-actions/configure-aws-credentials@v4",
            with_args={"aws-region": "us-east-1", "role-to-assume": "${{ secrets.AWS_ROLE }}"},
        )

    # Retrieve pipeline and transpile
    pipe = register_pipeline(pipeline_name)
    tr = GitHubTranspiler(pipe)
    yaml_out = tr.to_yaml()

    assert_matches_golden(yaml_out, "test_uses_action.yml")
