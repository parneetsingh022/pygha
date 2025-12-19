import sys
import re
from pathlib import Path


def bump_version(current_version, bump_type):
    """Increments the version string based on SemVer rules."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?", current_version)
    if not match:
        raise ValueError(f"Invalid version format found: {current_version}")

    major, minor, patch, rc = match.groups()
    major, minor, patch = int(major), int(minor), int(patch)
    rc = int(rc) if rc else None

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        if rc is not None:
            return f"{major}.{minor}.{patch}"
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "rc":
        if rc is None:
            return f"{major}.{minor}.{patch + 1}rc1"
        else:
            return f"{major}.{minor}.{patch}rc{rc + 1}"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}. Use major/minor/patch/rc.")


def update_file(path, regex, replacement):
    """Utility to perform anchored regex replacement."""
    if not path.exists():
        print(f"Warning: {path} not found. Skipping.")
        return
    content = path.read_text(encoding="utf-8")
    # Using re.MULTILINE so ^ matches the start of each line
    new_content = re.sub(regex, replacement, content, flags=re.MULTILINE)
    path.write_text(new_content, encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print("Usage: python version_bump.py (major|minor|patch|rc)")
        sys.exit(1)

    bump_type = sys.argv[1].lower()

    pyproject_path = Path("pyproject.toml")
    init_path = Path("src/pygha/__init__.py")
    meta_path = Path("recipe/meta.yaml")

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found.")
        sys.exit(1)

    content = pyproject_path.read_text(encoding="utf-8")
    # Find only the version line that starts with 'version ='
    version_match = re.search(r'^version\s*=\s*"(.*?)"', content, flags=re.MULTILINE)
    if not version_match:
        print("Error: Could not find main version string in pyproject.toml")
        sys.exit(1)

    current_version = version_match.group(1)

    try:
        new_version = bump_version(current_version, bump_type)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Bumping version: {current_version} -> {new_version}")

    # 1. Update pyproject.toml (only matches line starting with 'version =')
    update_file(pyproject_path, r'^version\s*=\s*".*?"', f'version = "{new_version}"')

    # 2. Update __init__.py (only matches line starting with '__version__ =')
    update_file(init_path, r'^__version__\s*=\s*".*?"', f'__version__ = "{new_version}"')

    # 3. Update recipe/meta.yaml (only matches line starting with '  version:')
    update_file(meta_path, r'^  version:\s*".*?"', f'  version: "{new_version}"')

    print("Successfully updated version strings without touching target-version.")


if __name__ == "__main__":
    main()
