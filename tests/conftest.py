import os
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def golden_dir() -> Path:
    # Put goldens next to the tests
    return Path(__file__).parent / "golden"


def _read_text(path: Path) -> str:
    # Normalize newlines so tests are stable on Windows/macOS/Linux
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.fixture
def assert_matches_golden(golden_dir: Path):
    """
    Usage: assert_matches_golden(actual_text, "file.yml")
    If UPDATE_GOLDEN=1 is set in env, rewrite the golden.
    """
    def _inner(actual: str, golden_name: str):
        golden_path = golden_dir / golden_name
        actual_norm = actual.replace("\r\n", "\n")

        if os.getenv("UPDATE_GOLDEN") == "1":
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(actual_norm, encoding="utf-8")
            # Still assert, to catch accidental env left on in CI
            expected = _read_text(golden_path)
            assert actual_norm == expected, f"rewrote {golden_name}, but mismatch remains"

        else:
            assert golden_path.exists(), f"Golden file missing: {golden_path}"
            expected = _read_text(golden_path)
            assert actual_norm == expected, (
                f"Golden mismatch for {golden_name}.\n"
                f"--- EXPECTED ({golden_name}) ---\n{expected}\n"
                f"--- ACTUAL ---\n{actual_norm}\n"
                f"Tip: set UPDATE_GOLDEN=1 to accept changes."
            )
    return _inner
