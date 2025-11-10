from typing import Dict
from .models import Pipeline

# Global registry of pipelines
_pipelines: Dict[str, Pipeline] = {"default": Pipeline()}

def get_default() -> Pipeline:
    return _pipelines["default"]

def get_pipeline(name: str) -> Pipeline:
    return _pipelines[name]

def register_pipeline(name: str):
    if name not in _pipelines:
        _pipelines[name] = Pipeline()
    return _pipelines[name]
