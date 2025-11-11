"""Pipeline registry module.

This module provides a global registry for managing `Pipeline` instances.
It allows registering, retrieving, and accessing the default pipeline.

Notes:
    - Registering a pipeline with an existing name will return the existing
      instance rather than creating a new one.
    - The default pipeline is always available under the name "default".
"""

from typing import Dict
from .models import Pipeline

# Global registry of pipelines
_pipelines: Dict[str, Pipeline] = {"default": Pipeline(name='ci')}


def get_default() -> Pipeline:
    """Return the default pipeline instance.

    Returns:
        Pipeline: The default registered pipeline.
    """
    return _pipelines["default"]


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