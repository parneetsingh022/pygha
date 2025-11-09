# tests/test_steps.py
import subprocess
from unittest.mock import patch

import pytest

# Adjust import to your package layout if needed
from pypipe.steps import RunShellStep, CheckoutStep


# -------------------
# RunShellStep tests
# -------------------

def test_runshellstep_default_name_short_command():
    step = RunShellStep(command="pytest", name=None)
    assert step.name == "run: pytest"

def test_runshellstep_default_name_long_command_truncated():
    long_cmd = "a" * 41  # > 40 chars triggers truncation to 37 + "..."
    step = RunShellStep(command=long_cmd, name=None)
    assert step.name == f"run: {'a' * 37}..."

def test_runshellstep_respects_explicit_name():
    step = RunShellStep(command="echo hi", name="Custom Name")
    assert step.name == "Custom Name"

def test_runshellstep_to_github_dict():
    step = RunShellStep(command="pytest -q", name="Run tests")
    out = step.to_github_dict()
    assert out == {"name": "Run tests", "run": "pytest -q"}

def test_runshellstep_to_gitlab_dict():
    step = RunShellStep(command="pytest -q", name="Run tests")
    out = step.to_gitlab_dict()
    assert out == {"name": "Run tests", "script": "pytest -q"}

def test_runshellstep_execute_invokes_subprocess_run(monkeypatch):
    recorded = {}

    def fake_run(cmd, shell, check, text, encoding):
        recorded["args"] = (cmd, shell, check, text, encoding)
        return None

    monkeypatch.setattr(subprocess, "run", fake_run)
    step = RunShellStep(command="echo hello", name="Say hello")
    step.execute(context={})
    assert recorded["args"] == ("echo hello", True, True, True, "utf-8")

def test_runshellstep_execute_raises_calledprocesserror(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=7, cmd="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    step = RunShellStep(command="boom", name="Explode")
    with pytest.raises(subprocess.CalledProcessError) as exc:
        step.execute(context={})
    assert exc.value.returncode == 7

def test_runshellstep_execute_raises_other_exception(monkeypatch):
    class Weird(Exception):
        pass

    def fake_run(*args, **kwargs):
        raise Weird("oops")

    monkeypatch.setattr(subprocess, "run", fake_run)
    step = RunShellStep(command="weird", name="Weird")
    with pytest.raises(Weird):
        step.execute(context={})


# -------------------
# CheckoutStep tests
# -------------------

def test_checkoutstep_default_name_when_absent():
    step = CheckoutStep(repository=None, ref=None, name=None)
    assert step.name == "Checkout code"

def test_checkoutstep_respects_explicit_name():
    step = CheckoutStep(repository=None, ref=None, name="Fetch sources")
    assert step.name == "Fetch sources"

def test_checkoutstep_execute_prints_simulation_without_repo(capsys, monkeypatch):
    # Ensure we don't accidentally call subprocess.run
    with patch.object(subprocess, "run") as run_mock:
        step = CheckoutStep(repository=None, ref=None, name="Checkout code")
        step.execute(context={})
        run_mock.assert_not_called()

    out = capsys.readouterr().out
    # Should show the step header and a simple 'git clone' without URL
    assert "--- Running step: Checkout code" in out
    assert "[Simulating] git clone" in out
    assert "github.com" not in out  # no repo URL printed

def test_checkoutstep_execute_prints_simulation_with_repo(capsys, monkeypatch):
    with patch.object(subprocess, "run") as run_mock:
        step = CheckoutStep(repository="user/repo", ref=None, name="Checkout code")
        step.execute(context={})
        run_mock.assert_not_called()

    out = capsys.readouterr().out
    assert "--- Running step: Checkout code" in out
    assert "[Simulating] git clone https://github.com/user/repo.git" in out

def test_checkoutstep_to_github_dict_minimal():
    step = CheckoutStep(repository=None, ref=None, name="Checkout code")
    out = step.to_github_dict()
    # 'with' block should be omitted when empty
    assert out == {
        "name": "Checkout code",
        "uses": "actions/checkout@v4",
    }
    assert "with" not in out

def test_checkoutstep_to_github_dict_with_details():
    step = CheckoutStep(repository="user/repo", ref="main", name="Checkout code")
    out = step.to_github_dict()
    assert out["name"] == "Checkout code"
    assert out["uses"] == "actions/checkout@v4"
    assert out["with"] == {"repository": "user/repo", "ref": "main"}

def test_checkoutstep_to_gitlab_dict_with_repo():
    step = CheckoutStep(repository="user/repo", ref=None, name="Checkout code")
    out = step.to_gitlab_dict()
    assert out == {
        "name": "Checkout code",
        "script": "git clone https://gitlab.com/user/repo.git",
    }

def test_checkoutstep_to_gitlab_dict_without_repo_returns_empty():
    step = CheckoutStep(repository=None, ref=None, name="Checkout code")
    out = step.to_gitlab_dict()
    assert out == {}

def test_checkoutstep_execute_handles_exception(monkeypatch):
    step = CheckoutStep(repository="user/repo", name="Checkout code")

    # Replace print with something that raises, to simulate a failure
    def fake_print(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("builtins.print", fake_print)

    with pytest.raises(RuntimeError, match="simulated failure"):
        step.execute(context={})
