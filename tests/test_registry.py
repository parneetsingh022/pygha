# tests/test_registry.py
import importlib
import pytest

from pygha import registry
from pygha.models import Pipeline, Job
from pygha import pipeline, default_pipeline


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    """
    Ensure every test starts from a known registry state.

    We reset the internal _pipelines map to only contain a fresh 'default'
    pipeline, so tests don't leak state across each other.
    """
    # Reload registry to ensure module-level side effects are reset (optional).
    importlib.reload(registry)

    monkeypatch.setattr(registry, "_pipelines", {"default": Pipeline(name="ci")})
    yield


def test_default_pipeline_exists_and_is_pipeline():
    pipe = registry.get_default()
    assert isinstance(pipe, Pipeline)

    # Default should be present in the internal map
    assert "ci" in registry._pipelines
    assert registry._pipelines["ci"] is pipe


def test_register_pipeline_creates_and_returns_pipeline():
    foo = registry.register_pipeline("foo")
    assert isinstance(foo, Pipeline)
    # It should be retrievable and identical object
    assert registry.get_pipeline("foo") is foo
    # Should not clobber default
    assert registry.get_default() is registry._pipelines["ci"]


def test_register_pipeline_is_idempotent_same_object():
    p1 = registry.register_pipeline("builds")
    p2 = registry.register_pipeline("builds")
    assert p1 is p2  # same instance returned on repeated registration


def test_get_pipeline_raises_for_missing_name():
    with pytest.raises(KeyError):
        registry.get_pipeline("does-not-exist")


def test_pipelines_are_isolated_jobs_do_not_bleed():
    # Create two pipelines
    a = registry.register_pipeline("a")
    b = registry.register_pipeline("b")

    # Add a job to 'a' only
    a.add_job(Job(name="compile"))

    assert "compile" in a.jobs
    assert "compile" not in b.jobs
    assert "compile" not in registry.get_default().jobs


def test_jobs_added_via_object_are_reflected_in_registry_map():
    p = registry.register_pipeline("ci")
    job = Job(name="test")
    p.add_job(job)

    # Access same pipeline via registry map and verify the job exists
    same_p = registry.get_pipeline("ci")
    assert "test" in same_p.jobs
    assert same_p.jobs["test"] is job


def test_default_pipeline_is_stable_object():
    d1 = registry.get_default()
    d2 = registry.get_default()
    assert d1 is d2


def test_unknown_kwargs_in_pipeline_raises_type_error():
    """Ensure that unexpected kwargs raise TypeError for both pipeline functions."""
    with pytest.raises(TypeError):
        pipeline(on_push=True, on_pull_request=True, wrong_arg=True)

    with pytest.raises(TypeError):
        default_pipeline(on_push=True, on_pull_request=True, wrong_arg=True)
