from dataclasses import dataclass
from typing import Any, Union, TypedDict

Trigger = Union[str, list[str], dict[str, Any], bool, None]


class PipelineSettingsKwargs(TypedDict, total=False):
    on_push: Trigger
    on_pull_request: Trigger


@dataclass
class PipelineSettings:
    """
    Settings for a pipeline. Designed to be serializable to/from JSON.
    """

    on_push: Trigger = None
    on_pull_request: Trigger = None

    def _transpile_trigger(self, config: Any) -> dict[str, Any] | None:
        """
        Internal helper to "transpile" the user-friendly
        input into the required GitHub Actions dict.
        """

        # Case 1: User passed a single branch string
        # e.g., on_push="main"
        if isinstance(config, str):
            return {"branches": [config]}

        # Case 2: User passed a list of branches
        # e.g., on_push=["main", "dev"]
        if isinstance(config, list):
            # An empty list means "disable this trigger"
            if not config:
                return None
            return {"branches": config}

        # Case 3: User passed True (just enable it)
        # e.g., on_push=True
        if config is True:
            return None  # True means trigger on all branches/events (no filters)

        # Case 4: User passed a full dict (power user)
        # e.g., on_push={"branches": ["main"], "paths": ["src/**"]}
        if isinstance(config, dict):
            return config

        # If it's None or False, we'll skip it.
        if config is None or config is False:
            return None

        raise TypeError(
            f"Invalid config type for a trigger: {type(config).__name__}. "
            f"Expected str, list, dict, bool, or None, got {config!r}"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Returns the dictionary for the 'on:' block in a
        GitHub Actions workflow.
        """
        on_section: dict[str, Any] = {}

        # Transpile the "magic" inputs
        push_config = self._transpile_trigger(self.on_push)
        if push_config is not None or self.on_push is True:
            on_section["push"] = push_config

        pr_config = self._transpile_trigger(self.on_pull_request)
        if pr_config is not None or self.on_pull_request is True:
            on_section["pull_request"] = pr_config

        # --- Defaulting Logic ---
        # If, after all that, on_section is still empty
        # (e.g., user set on_push=None), add a default.
        if not on_section:
            # Default to push on "main"
            on_section["push"] = {"branches": ["main"]}

        return on_section
