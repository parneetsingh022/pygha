"""Pipeline registry module.

This module provides a global registry for managing `Pipeline` instances.
It allows registering, retrieving, and accessing the default pipeline.

Notes:
    - Registering a pipeline with an existing name will return the existing
      instance rather than creating a new one.
    - The default pipeline is always available under the name "default".
"""

from typing import Dict, Any
from .models import Pipeline
from .trigger_event import PipelineSettings

# Global registry of pipelines
_pipelines: Dict[str, Pipeline] = {"ci": Pipeline(name='ci')}


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


def pipeline(name: str, **kwargs: Any) -> Pipeline:
    """
    Get, create, or configure a pipeline's settings.

    This is the main user-facing function for setting pipeline-level
    options like 'on_push' or 'on_pull_request'.

    Args:
        name (str): The name of the pipeline.
        **kwargs: Any valid arguments for the PipelineSettings
                  dataclass (e.g., on_push="main", on_pull_request=True).
    
    Returns:
        Pipeline: The configured pipeline instance.
    """
    # 1. Get-or-create the pipeline object using your existing function
    pipe_instance = register_pipeline(name)
    
    # 2. Create a new settings object from all the user's kwargs
    #    The 'name' from PipelineSettings is for the YAML, not the key.
    if 'name' not in kwargs:
        kwargs['name'] = pipe_instance.name

    new_settings = PipelineSettings(**kwargs)
    
    # 3. Overwrite the pipeline's default settings with the new ones
    pipe_instance.pipeline_settings = new_settings
    
    return pipe_instance

def default_pipeline(**kwargs: Any) -> Pipeline:
    return pipeline(name='ci', **kwargs)


def reset_registry() -> None:
    """Reset the global pipeline registry to its initial state.

    This clears all registered pipelines and recreates the default 'ci' pipeline.
    Useful for ensuring test isolation between runs.
    """
    global _pipelines
    _pipelines.clear()
    _pipelines["ci"] = Pipeline(name="ci")