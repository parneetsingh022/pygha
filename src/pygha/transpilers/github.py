import re
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from typing import Any

from collections.abc import MutableMapping

from collections.abc import Iterable
from ..models import Pipeline, Job
from ..registry import get_default


class GitHubTranspiler:
    def __init__(self, pipeline: Pipeline | None = None):
        self.pipeline = pipeline if pipeline is not None else get_default()

    @staticmethod
    def _sorted_unique(items: Iterable[str]) -> list[str]:
        # Ensure deterministic, duplicate-free 'needs'
        return sorted(set(items))

    def _extract_vars(self, text: str) -> set[str]:
        """Extracts 'matrix.xxx' from a string like '${{ matrix.xxx }}'."""
        # Matches ${{ matrix.os }}, ${{ matrix.python-version }}, etc.
        return set(re.findall(r"\$\{\{\s*matrix\.([\w-]+)\s*\}\}", text))

    def _scan_for_vars(self, data: Any) -> set[str]:
        """Recursively scans a dict, list, or string for matrix variables."""
        found = set()
        if isinstance(data, str):
            found.update(self._extract_vars(data))
        elif isinstance(data, dict):
            for value in data.values():
                found.update(self._scan_for_vars(value))
        elif isinstance(data, list):
            for item in data:
                found.update(self._scan_for_vars(item))
        return found

    def _validate_matrix(self, job: Job, job_dict: dict[str, Any]) -> None:
        """Ensures all matrix variables used in the job are actually defined."""
        used_vars = self._scan_for_vars(job_dict)

        if not used_vars:
            return

        if not job.matrix:
            # Get the first invalid variable found for the error message
            invalid = next(iter(used_vars))
            raise ValueError(
                f"Job '{job.name}' uses '${{{{ matrix.{invalid} }}}}' but has no matrix defined."
            )

        valid_keys = {k for k in job.matrix.keys() if k not in ("include", "exclude")}

        if "include" in job.matrix:
            for item in job.matrix["include"]:
                if isinstance(item, dict):
                    valid_keys.update(item.keys())

        unknowns = used_vars - valid_keys
        if unknowns:
            raise ValueError(
                f"Job '{job.name}' uses undefined matrix variables: {sorted(unknowns)}. "
                f"Available keys: {sorted(valid_keys)}"
            )

    def to_dict(self) -> MutableMapping[str, Any]:
        jobs_dict: dict[str, Any] = {}

        for job in self.pipeline.get_job_order():
            job_dict: dict[str, Any] = {
                "runs-on": job.runner_image or "ubuntu-latest",
            }

            if job.if_condition:
                job_dict["if"] = job.if_condition

            if job.timeout_minutes is not None:
                job_dict["timeout-minutes"] = job.timeout_minutes

            if job.matrix:
                strategy: dict[str, Any] = {"matrix": job.matrix}

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

            job_dict["steps"] = steps_list

            self._validate_matrix(job, job_dict)

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
