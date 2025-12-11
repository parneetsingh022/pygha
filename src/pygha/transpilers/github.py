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

            if job.if_condition:
                job_dict["if"] = job.if_condition

            if job.matrix:
                strategy: dict[str, Any] = {"matrix": job.matrix}

                # Only add fail-fast if the user explicitly set it (True or False)
                if job.fail_fast is not None:
                    strategy["fail-fast"] = job.fail_fast

                job_dict["strategy"] = strategy

            if job.depends_on:
                deps = self._sorted_unique(job.depends_on)
                job_dict["needs"] = deps

            steps_list = []
            for step in job.steps:
                d = step.to_github_dict()
                if step.if_condition:
                    # Insert 'if' at the top level of the step dict
                    # (Order doesn't strictly matter for JSON/YAML dicts,
                    # but usually 'if' is near 'name' or 'run')
                    d["if"] = step.if_condition
                steps_list.append(d)

            # Now add steps
            job_dict["steps"] = steps_list

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
        yaml12.width = 4096

        from io import StringIO

        buffer = StringIO()
        yaml12.dump(self.to_dict(), buffer)
        return buffer.getvalue()
