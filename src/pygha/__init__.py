# pygha/__init__.py
from .decorators import job
from pygha.registry import pipeline, default_pipeline

__version__ = "0.1.0"
__all__ = ["job", "pipeline", "default_pipeline"]
