import pytest
from pygha import job
from pygha.steps import shell, checkout, when, uses
from pygha.decorators import run_if
from pygha.expr import github, always, failure
from pygha.transpilers.github import GitHubTranspiler
from pygha.registry import reset_registry
from pygha.expr import runner, env, success


@pytest.fixture(autouse=True)
def clean():
    reset_registry()


def test_expr_builder():
    """Verify python operators convert to GHA strings."""
    expr = (github.ref == "main") & (github.event_name != "pull_request")
    assert str(expr) == "(github.ref == 'main') && (github.event_name != 'pull_request')"


def test_context_manager_basic():
    """Verify steps inside 'when' get the condition."""

    @job(name="test")
    def my_job():
        with when("runner.os == 'Linux'"):
            shell("echo linux")
        shell("echo always")

    # Manually inspect the pipeline
    from pygha.registry import get_default

    j = get_default().jobs["test"]

    assert j.steps[0].if_condition == "runner.os == 'Linux'"
    assert j.steps[1].if_condition is None


def test_context_manager_nested():
    """Verify nested 'when' blocks combine with AND."""

    @job(name="test")
    def my_job():
        with when("A"):
            with when("B"):
                shell("echo nested")

    from pygha.registry import get_default

    j = get_default().jobs["test"]
    # Should be (A) && (B)
    assert j.steps[0].if_condition == "(A) && (B)"


def test_run_if_decorator():
    """Verify @run_if applies to the job."""

    @job(name="conditional-job")
    @run_if(github.event_name == "push")
    def my_job():
        pass

    from pygha.registry import get_default

    j = get_default().jobs["conditional-job"]
    assert j.if_condition == "github.event_name == 'push'"


def test_expr_types_handling():
    """Verify comparisons with integers and booleans do not get quoted."""
    # Integer comparison (should not have quotes)
    expr_int = github.run_attempt == 1
    assert str(expr_int) == "github.run_attempt == 1"

    # Boolean comparison (should not have quotes)
    expr_bool = runner.debug == True  # noqa: E712
    assert str(expr_bool) == "runner.debug == True"

    # String comparison (should have quotes)
    expr_str = github.ref == "main"
    assert str(expr_str) == "github.ref == 'main'"


def test_sibling_when_blocks():
    """Verify that sequential when blocks do not leak conditions to each other."""

    @job(name="sibling-test")
    def my_job():
        # Block A
        with when("A"):
            shell("step 1")

        # Block B (Should NOT have A)
        with when("B"):
            shell("step 2")

    from pygha.registry import get_default

    j = get_default().jobs["sibling-test"]

    assert j.steps[0].if_condition == "A"
    assert j.steps[1].if_condition == "B"
    # If the stack didn't pop correctly, this might have been "(A) && (B)"


def test_uses_helper_with_condition():
    """Verify the generic uses() helper accepts conditions."""

    @job(name="uses-test")
    def my_job():
        with when("runner.os == 'Windows'"):
            uses("actions/setup-python@v5", with_args={"python-version": "3.10"})

    from pygha.registry import get_default

    j = get_default().jobs["uses-test"]

    step = j.steps[0]
    assert step.if_condition == "runner.os == 'Windows'"
    assert step.action == "actions/setup-python@v5"


def test_stacked_run_if_behavior():
    """
    Verify behavior when @run_if is used multiple times.
    Current implementation: The outermost decorator (top) runs last and overwrites attributes.
    """

    @job(name="overwrite-test")
    @run_if("condition_A")  # Top decorator
    @run_if("condition_B")  # Inner decorator
    def my_job():
        pass

    from pygha.registry import get_default

    j = get_default().jobs["overwrite-test"]

    # Confirms that 'condition_A' overwrites 'condition_B'
    # If you wanted them to AND together, this test would fail and indicate a need for code changes.
    assert j.if_condition == "condition_A"


def test_full_yaml_output(assert_matches_golden):
    """
    Integration test covering all major conditional scenarios:
    1. Job-level conditionals (@run_if)
    2. Simple step conditionals
    3. Nested conditionals (Implicit AND)
    4. Complex boolean logic (&, |, ~)
    5. Context helpers (github, runner, env)
    6. Function helpers (always, success, failure)
    """

    @job(name="complex-logic")
    @run_if(github.event_name == "push")  # Scenario 1: Job Condition
    def complex_job():
        # Scenario 2: No condition
        checkout()

        # Scenario 2: Simple comparison
        with when(runner.os == "Linux"):
            shell("echo 'Running on Linux'")

        # Scenario 4: Complex OR logic with string comparisons
        with when((github.ref == "refs/heads/main") | (github.event_name == "schedule")):
            shell("echo 'Prod or Schedule'")

        # Scenario 3: Nested conditions (Implicit AND)
        with when(env.DEPLOY_ENV != "production"):
            shell("echo 'Not production'")

            # This step inherits the outer condition + its own
            with when(success()):
                shell("echo 'Previous steps succeeded AND not prod'")

        # Scenario 4: Negation (NOT)
        with when(~(github.actor == "dependabot")):
            shell("echo 'Not a bot'")

        # Scenario 4: Complex AND logic
        with when((github.actor == "admin") & (runner.arch == "X64")):
            shell("echo 'Admin on X64'")

        # Scenario 6: Function helper (always runs even if previous failed)
        with when(always()):
            shell("echo 'Cleanup or finalize'")

        # Scenario 6: Failure check
        with when(failure()):
            shell("echo 'Something failed earlier'")

    tr = GitHubTranspiler()
    assert_matches_golden(tr.to_yaml(), "test_conditions.yml")
