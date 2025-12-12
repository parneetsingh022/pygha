import tomllib  # Python 3.11+
from pathlib import Path
from ruamel.yaml import YAML
import pygha


def test_version_matches_pyproject():
    """
    Ensures that the version string in __init__.py matches both
    pyproject.toml and recipe/meta.yaml.
    """

    root_dir = Path(__file__).parents[1]

    # Check pyproject.toml
    with open(root_dir / "pyproject.toml", "rb") as f:
        pyproject_version = tomllib.load(f)["project"]["version"]
    assert pygha.__version__ == pyproject_version, "Version mismatch in pyproject.toml"

    # Check recipe/meta.yaml
    yaml = YAML(typ="safe")
    with open(root_dir / "recipe/meta.yaml", encoding="utf-8") as f:
        meta_config = yaml.load(f)
        recipe_version = meta_config["package"]["version"]

    assert pygha.__version__ == recipe_version, "Version mismatch in recipe/meta.yaml"
