import pytest
from pygha.models import Job, Pipeline
from pygha.transpilers.github import GitHubTranspiler
from pygha.steps.builtin import RunShellStep, UsesStep
from pygha import matrix


# --- Helper to create a quick transpiler for a single job ---
def transpile_job(job: Job):
    pipeline = Pipeline(name="test-pipe")
    pipeline.add_job(job)
    transpiler = GitHubTranspiler(pipeline)
    return transpiler.to_dict()


# --- Tests ---


def test_matrix_validation_success():
    """Test that valid matrix usage passes without error."""
    job = Job(
        name="test-job",
        matrix={"os": ["ubuntu-latest", "windows-latest"], "version": ["3.10", "3.11"]},
        runner_image="${{ matrix.os }}",
        steps=[RunShellStep(command="echo ${{ matrix.version }}")],
    )
    # Should not raise
    transpile_job(job)


def test_matrix_validation_success_with_include():
    """Test that variables defined ONLY in 'include' are considered valid."""
    job = Job(
        name="test-include",
        matrix={
            "os": ["ubuntu-latest"],
            "include": [
                {"os": "ubuntu-latest", "experimental": "true"},
                {"os": "windows-latest", "experimental": "false"},
            ],
        },
        steps=[RunShellStep(command="echo Is Experimental: ${{ matrix.experimental }}")],
    )
    # Should not raise
    transpile_job(job)


def test_fail_usage_without_matrix_defined():
    """Test using matrix vars when no matrix is defined at all."""
    job = Job(name="oops-job", matrix=None, steps=[RunShellStep(command="echo ${{ matrix.os }}")])

    with pytest.raises(ValueError) as exc:
        transpile_job(job)

    assert "Job 'oops-job' uses '${{ matrix.os }}' but has no matrix defined" in str(exc.value)


def test_fail_undefined_variable():
    """Test using a variable that isn't in the matrix keys."""
    job = Job(
        name="typo-job",
        matrix={"os": ["ubuntu-latest"]},
        steps=[
            # 'python-version' is not in the matrix keys
            RunShellStep(command="echo ${{ matrix.python-version }}")
        ],
    )

    with pytest.raises(ValueError) as exc:
        transpile_job(job)

    assert "Job 'typo-job' uses undefined matrix variables: ['python-version']" in str(exc.value)
    assert "Available keys: ['os']" in str(exc.value)


def test_validation_catches_runs_on():
    """Test that validation checks the 'runs-on' field."""
    job = Job(
        name="bad-runner",
        matrix={"os": ["ubuntu"]},
        # Typo in runs-on: 'oss' instead of 'os'
        runner_image="${{ matrix.oss }}",
        steps=[RunShellStep(command="echo hi")],
    )

    with pytest.raises(ValueError) as exc:
        transpile_job(job)

    assert "undefined matrix variables: ['oss']" in str(exc.value)


def test_validation_catches_if_condition():
    """Test that validation checks 'if' conditions on the job."""
    job = Job(
        name="conditional-job",
        matrix={"type": ["main", "fork"]},
        # 'branch' is not defined
        if_condition="${{ matrix.branch }} == 'main'",
        steps=[RunShellStep(command="echo hi")],
    )

    with pytest.raises(ValueError) as exc:
        transpile_job(job)

    assert "undefined matrix variables: ['branch']" in str(exc.value)


def test_validation_catches_nested_uses_args():
    """Test that validation recursively checks nested dictionaries (like with_args)."""
    job = Job(
        name="nested-job",
        matrix={"python": ["3.11"]},
        steps=[
            UsesStep(
                action="actions/setup-python@v5",
                with_args={
                    "python-version": "${{ matrix.python }}",  # Valid
                    "cache": "${{ matrix.caching }}",  # Invalid!
                },
            )
        ],
    )

    with pytest.raises(ValueError) as exc:
        transpile_job(job)

    assert "undefined matrix variables: ['caching']" in str(exc.value)


def test_multiple_invalid_vars():
    """Test that it reports all missing variables."""
    job = Job(
        name="multi-fail",
        matrix={"a": [1]},
        steps=[RunShellStep(command="echo ${{ matrix.b }} and ${{ matrix.c }}")],
    )

    with pytest.raises(ValueError) as exc:
        transpile_job(job)

    msg = str(exc.value)
    assert "undefined matrix variables" in msg
    assert "'b'" in msg
    assert "'c'" in msg


def test_ignores_standard_vars():
    """Ensure it doesn't accidentally flag ${{ github.sha }} or ${{ secrets.TOKEN }}."""
    job = Job(
        name="standard-vars",
        matrix={"os": ["ubuntu"]},
        steps=[
            RunShellStep(command="echo ${{ github.sha }} ${{ secrets.MY_TOKEN }} ${{ matrix.os }}")
        ],
    )
    # Should pass because it only looks for "matrix.xxx"
    transpile_job(job)


def test_no_leakage_between_jobs():
    """
    Ensure that Job B doesn't accidentally 'see' Job A's matrix variables.
    """
    # Job A has a valid matrix
    job_a = Job(
        name="job-a",
        matrix={"os": ["linux"]},
        steps=[RunShellStep(command="echo ${{ matrix.os }}")],
    )

    # Job B has NO matrix, but tries to use Job A's variable
    job_b = Job(
        name="job-b",
        matrix=None,
        steps=[RunShellStep(command="echo ${{ matrix.os }}")],  # Should fail!
    )

    pipeline = Pipeline(name="leak-test")
    pipeline.add_job(job_a)
    pipeline.add_job(job_b)

    # We expect this to fail because Job B is invalid
    with pytest.raises(ValueError) as exc:
        GitHubTranspiler(pipeline).to_dict()

    # The error must specifically be about Job B
    assert "Job 'job-b' uses '${{ matrix.os }}' but has no matrix defined" in str(exc.value)


def test_matrix_proxy_returns_correct_format():
    """
    Unit test to verify that the MatrixProxy returns the exact
    GitHub Actions expression format string.
    """
    # Verify strict string equality
    assert str(matrix.os) == "${{ matrix.os }}"
    assert str(matrix.python_version) == "${{ matrix.python-version }}"
    assert str(matrix["python-version"]) == "${{ matrix.python-version }}"
    assert str(matrix["python_version"]) == "${{ matrix.python_version }}"

    # Verify it works inside an f-string
    assert f"echo {matrix.test}" == "echo ${{ matrix.test }}"


def test_matrix_proxy_integration_success():
    """
    Test that using the Python 'matrix' object for a VALID variable
    passes validation correctly.
    """
    job = Job(
        name="proxy-success-test",
        matrix={"os": ["ubuntu-latest"]},
        steps=[
            # User uses matrix.os, which is valid
            RunShellStep(command=f"echo Running on {matrix.os}")
        ],
    )

    # Should pass without error
    result = transpile_job(job)

    # Verify the output contains the transpiled string
    step_cmd = result["jobs"]["proxy-success-test"]["steps"][0]["run"]
    assert step_cmd == "echo Running on ${{ matrix.os }}"


def test_matrix_proxy_object_integration():
    """
    Test that using the Python 'matrix' object (instead of raw strings)
    correctly triggers validation errors.
    """
    # 1. Use the matrix object in an f-string (e.g., f"{matrix.typo}")
    # This simulates exactly what a user writes in their pipeline code.
    job = Job(
        name="proxy-integration-test",
        matrix={"os": ["ubuntu"]},
        steps=[
            RunShellStep(command=f"echo {matrix.typo}")  # User writes matrix.typo
        ],
    )

    # 2. Transpile and expect failure
    # The transpiler should see "${{ matrix.typo }}" and flag it.
    with pytest.raises(ValueError) as exc:
        transpile_job(job)

    assert "undefined matrix variables: ['typo']" in str(exc.value)


def test_matrix_proxy_integration_hyphen():
    """Test using dictionary syntax for keys with hyphens."""
    job = Job(
        name="hyphen-test",
        matrix={"python-version": ["3.11"]},
        steps=[
            # User must use brackets for keys with hyphens
            RunShellStep(command=f"echo {matrix['python-version']}")
        ],
    )

    transpile_job(job)


def test_matrix_proxy_integration_underscore():
    """Test using dot syntax for keys with underscores."""
    job = Job(
        name="underscore-test",
        matrix={"custom_val": ["x"]},
        steps=[
            # User uses dot notation for valid Python identifiers
            RunShellStep(command=f"echo {matrix['custom_val']}")
        ],
    )

    transpile_job(job)
