from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from typing import Any

from collections.abc import MutableMapping

from collections.abc import Iterable
from ..models import Pipeline
from ..registry import get_default


class GitHubTranspiler:
    def __init__(self, pipeline: Pipeline | None = None):
        self.pipeline = pipeline if pipeline is not None else get_default()

    @staticmethod
    def _sorted_unique(items: Iterable[str]) -> list[str]:
        # Ensure deterministic, duplicate-free 'needs'
        return sorted(set(items))

    def to_dict(self) -> MutableMapping[str, Any]:
        jobs_dict: dict[str, Any] = {}

        for job in self.pipeline.get_job_order():
            job_dict: dict[str, Any] = {
                "runs-on": job.runner_image or "ubuntu-latest",
            }

            # Add 'needs' before 'steps'
            if job.depends_on:
                deps = self._sorted_unique(job.depends_on)
                job_dict["needs"] = deps

            # Now add steps
            job_dict["steps"] = [step.to_github_dict() for step in job.steps]

            jobs_dict[job.name] = job_dict

        workflow: MutableMapping[str, Any] = CommentedMap()
        workflow["name"] = self.pipeline.name
        workflow["on"] = self.pipeline.pipeline_settings.to_dict()
        workflow["jobs"] = jobs_dict

        return workflow

    def to_yaml(self) -> str:
        yaml12 = YAML()
        yaml12.indent(mapping=2, sequence=4, offset=2)
        yaml12.default_flow_style = False

        from io import StringIO

        buffer = StringIO()
        yaml12.dump(self.to_dict(), buffer)
        return buffer.getvalue()
