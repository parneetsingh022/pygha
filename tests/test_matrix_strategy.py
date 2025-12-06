import pytest
from pygha.models import Job
from pygha.decorators import job
from pygha.transpilers.github import GitHubTranspiler
from pygha.registry import reset_registry, register_pipeline
from pygha.steps import shell
from pygha.models import Pipeline

# --- 1. Model Tests ---


def test_job_model_stores_matrix_fields():
    """Test that the Job dataclass correctly stores matrix and fail_fast."""
    matrix_conf = {"os": ["ubuntu-latest", "windows-latest"]}

    j = Job(name="test", matrix=matrix_conf, fail_fast=False)

    assert j.matrix == matrix_conf
    assert j.fail_fast is False


def test_job_model_defaults():
    """Test that new fields default to None."""
    j = Job(name="defaults")
    assert j.matrix is None
    assert j.fail_fast is None


# --- 2. Decorator Tests ---


@pytest.fixture(autouse=True)
def clean_registry():
    reset_registry()


def test_decorator_passes_matrix_args():
    """Test that @job(matrix=...) populates the Job object correctly."""

    @job(name="matrix-job", matrix={"version": ["1.0", "2.0"]}, fail_fast=True)
    def my_job():
        pass

    # Retrieve the job from the default pipeline
    pipe = register_pipeline("ci")
    job_obj = pipe.jobs["matrix-job"]

    assert job_obj.matrix == {"version": ["1.0", "2.0"]}
    assert job_obj.fail_fast is True


# --- 3. Transpiler Tests (Unit) ---


def test_transpiler_generates_strategy_block():
    """Test that a Job with a matrix produces the correct 'strategy' dict."""
    # Manually create the job and pipeline (bypass decorator for unit test)
    job_obj = Job(name="test", matrix={"python": ["3.11", "3.12"]}, fail_fast=False)

    pipe = Pipeline(name="matrix-pipe")
    pipe.add_job(job_obj)

    tr = GitHubTranspiler(pipe)
    data = tr.to_dict()

    job_dict = data["jobs"]["test"]

    assert "strategy" in job_dict
    strategy = job_dict["strategy"]

    assert strategy["matrix"] == {"python": ["3.11", "3.12"]}
    assert strategy["fail-fast"] is False


def test_transpiler_omits_fail_fast_if_none():
    """Test that fail-fast is not included in YAML if it wasn't set (None)."""
    job_obj = Job(name="test", matrix={"os": ["linux"]})
    # fail_fast defaults to None

    pipe = Pipeline(name="matrix-pipe")
    pipe.add_job(job_obj)

    tr = GitHubTranspiler(pipe)
    data = tr.to_dict()

    strategy = data["jobs"]["test"]["strategy"]
    assert "matrix" in strategy
    assert "fail-fast" not in strategy


# --- 4. Golden / Integration Test ---


def test_full_yaml_output_with_matrix(assert_matches_golden):
    """
    Integration test: Define a matrix job and verify against golden file.
    """

    @job(
        name="test-matrix",
        runs_on="ubuntu-latest",
        matrix={"python-version": ["3.10", "3.11"]},
        fail_fast=False,
    )
    def matrix_job():
        pass

    pipe = register_pipeline("ci")
    tr = GitHubTranspiler(pipe)
    yaml_out = tr.to_yaml()

    # Pass the filename of the golden file we created in Step 1
    assert_matches_golden(yaml_out, "test_matrix_strategy.yml")


def test_matrix_os_expansion(assert_matches_golden):
    """
    Test that runs_on can successfully use the matrix context.
    """

    @job(
        name="test-os",
        # Verify we can inject the matrix variable here
        runs_on="${{ matrix.os }}",
        matrix={"os": ["ubuntu-latest", "windows-latest", "macos-latest"]},
    )
    def os_job():
        # Verify we can use it in a step too
        shell('echo "Running on ${{ matrix.os }}"')

    pipe = register_pipeline("ci")
    tr = GitHubTranspiler(pipe)
    assert_matches_golden(tr.to_yaml(), "test_matrix_os_expansion.yml")


def test_matrix_complex_include_exclude(assert_matches_golden):
    """
    Test that 'include' and 'exclude' (lists of dicts) render correctly
    within the matrix dictionary.
    """

    @job(
        name="test-complex",
        matrix={
            "version": ["10", "12"],
            "os": ["linux", "windows"],
            "include": [{"os": "macos", "version": "14", "experimental": True}],
            "exclude": [{"os": "windows", "version": "10"}],
        },
    )
    def complex_job():
        pass

    pipe = register_pipeline("ci")
    tr = GitHubTranspiler(pipe)
    assert_matches_golden(tr.to_yaml(), "test_matrix_complex.yml")
