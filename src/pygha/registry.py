"""Pipeline registry module.

This module provides a global registry for managing `Pipeline` instances.
It allows registering, retrieving, and accessing the default pipeline.

Notes:
    - Registering a pipeline with an existing name will return the existing
      instance rather than creating a new one.
    - The default pipeline is always available under the name "default".
"""

from typing import Unpack
from .models import Pipeline
from .trigger_event import PipelineSettings, PipelineSettingsKwargs
from dataclasses import fields

# Global registry of pipelines
_pipelines: dict[str, Pipeline] = {"ci": Pipeline(name="ci")}


def get_default() -> Pipeline:
    """Return the default pipeline instance.

    Returns:
        Pipeline: The default registered pipeline.
    """
    return register_pipeline("ci")


def get_pipeline(name: str) -> Pipeline:
    """Retrieve a pipeline by name.

    Args:
        name (str): The name of the pipeline to retrieve.

    Returns:
        Pipeline: The registered pipeline with the given name.

    Raises:
        KeyError: If no pipeline with the given name exists.
    """
    return _pipelines[name]


def register_pipeline(name: str) -> Pipeline:
    """Register a new pipeline if it does not already exist.

    If a pipeline with the given name is already registered,
    the existing pipeline is returned instead of creating a new one.

    Args:
        name (str): The name of the pipeline to register.

    Returns:
        Pipeline: The registered (new or existing) pipeline instance.
    """
    if name not in _pipelines:
        _pipelines[name] = Pipeline(name=name)
    return _pipelines[name]


def pipeline(name: str, **kwargs: Unpack[PipelineSettingsKwargs]) -> Pipeline:
    """
    Get, create, or configure a pipeline's settings.

    Keyword options:
      - on_push: str | list[str] | dict | True | None
      - on_pull_request: str | list[str] | dict | True | None
    """
    pipe_instance = register_pipeline(name)

    # --- Optional runtime guard for unknown keys (clearer errors) ---
    allowed = {f.name for f in fields(PipelineSettings)}
    unknown = set(kwargs).difference(allowed)
    if unknown:
        ks = ", ".join(sorted(unknown))
        raise TypeError(
            f"Unknown keyword argument(s): {ks}. " f"Allowed: {', '.join(sorted(allowed))}"
        )

    new_settings = PipelineSettings(**kwargs)
    pipe_instance.pipeline_settings = new_settings
    return pipe_instance


def default_pipeline(**kwargs: Unpack[PipelineSettingsKwargs]) -> Pipeline:
    return pipeline(name="ci", **kwargs)


def reset_registry() -> None:
    """Reset the global pipeline registry to its initial state.

    This clears all registered pipelines and recreates the default 'ci' pipeline.
    Useful for ensuring test isolation between runs.
    """
    global _pipelines
    _pipelines.clear()
    _pipelines["ci"] = Pipeline(name="ci")
