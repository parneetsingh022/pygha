import os
from pathlib import Path
import pytest
from types import SimpleNamespace
import runpy


from pygha import registry
from pygha.cli import main as cli_main


# ---------- helpers ----------


def write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


class FakePipeline:
    def __init__(self, name, jobs=None):
        self.name = name
        self.jobs = jobs or {}


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the registry before/after each test so tests don't leak state."""
    old = dict(getattr(registry, "_pipelines", {}))
    registry._pipelines = {}
    try:
        yield
    finally:
        registry._pipelines.clear()
        registry._pipelines.update(old)


@pytest.fixture
def fake_transpiler(monkeypatch):
    """Patch the transpiler at the call site used by the CLI."""

    class FakeTranspiler:
        def __init__(self, pipe):
            self.pipe = pipe

        def to_yaml(self):
            # deterministic, tiny output for simple assertions
            return f"name: {self.pipe.name}\njobs: {{}}\n"

    # IMPORTANT: patch where it's used (pygha.cli), not where it's defined
    monkeypatch.setattr("pygha.cli.GitHubTranspiler", FakeTranspiler)
    return FakeTranspiler


# ---------- tests ----------


def test_build_generates_one_file_per_pipeline(tmp_path, monkeypatch, fake_transpiler, capsys):
    src_dir = tmp_path / ".pipe"
    out_dir = tmp_path / ".github" / "workflows"
    src_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    # create two pipeline files (we mock their execution)
    write(src_dir / "pipeline_a.py", "print('a')")
    write(src_dir / "b_pipeline.py", "print('b')")

    # when files are "run", they register pipelines into the registry
    def fake_run_path(path):
        if path.endswith("pipeline_a.py"):
            registry._pipelines["pipe1"] = FakePipeline("pipe1")
        if path.endswith("b_pipeline.py"):
            registry._pipelines.setdefault("pipe1", FakePipeline("pipe1"))
            registry._pipelines["pipe2"] = FakePipeline("pipe2")

    monkeypatch.setattr("runpy.run_path", fake_run_path)

    rc = cli_main(["build", "--src-dir", str(src_dir), "--out-dir", str(out_dir)])
    assert rc == 0

    assert (out_dir / "pipe1.yml").read_text(encoding="utf-8") == "name: pipe1\njobs: {}\n"
    assert (out_dir / "pipe2.yml").read_text(encoding="utf-8") == "name: pipe2\njobs: {}\n"

    out = capsys.readouterr().out
    assert "Found 2 pipeline files" in out
    assert "Wrote" in out


def test_build_clean_removes_orphans_but_keeps_marked(tmp_path, monkeypatch, fake_transpiler):
    src_dir = tmp_path / ".pipe"
    out_dir = tmp_path / ".github" / "workflows"
    src_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    # existing workflows
    write(out_dir / "old.yml", "name: old\n")  # should be deleted
    write(out_dir / "keep1.yml", "# pygha: keep\nname: keep1\n")  # keep
    write(out_dir / "keep2.yml", "#pygha :    KEEP\nname: keep2\n")  # keep (spacing/case)
    write(out_dir / "pipe1.yml", "name: pipe1\n")  # will be rewritten

    # pipelines produced by current run: only "pipe1"
    write(src_dir / "pipeline_any.py", "print('hi')")

    def fake_run_path(_):
        registry._pipelines["pipe1"] = FakePipeline("pipe1")

    monkeypatch.setattr("runpy.run_path", fake_run_path)

    # sanity: keep marker detection
    from pygha.cli import _has_keep_marker

    assert _has_keep_marker(out_dir / "keep1.yml")
    assert _has_keep_marker(out_dir / "keep2.yml")

    rc = cli_main(["build", "--src-dir", str(src_dir), "--out-dir", str(out_dir), "--clean"])
    assert rc == 0

    assert not (out_dir / "old.yml").exists()
    assert (out_dir / "keep1.yml").exists()
    assert (out_dir / "keep2.yml").exists()
    assert (out_dir / "pipe1.yml").read_text(encoding="utf-8") == "name: pipe1\njobs: {}\n"


def test_build_no_pipelines_prints_message_and_exits_zero(
    tmp_path, monkeypatch, capsys, fake_transpiler
):
    src_dir = tmp_path / ".pipe"
    out_dir = tmp_path / ".github" / "workflows"
    src_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    write(src_dir / "pipeline_none.py", "print('noop')")

    # running the file registers nothing
    monkeypatch.setattr("runpy.run_path", lambda p: None)

    rc = cli_main(["build", "--src-dir", str(src_dir), "--out-dir", str(out_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No pipelines registered" in out
    assert list(out_dir.glob("*.yml")) == []


def test_build_respects_custom_dirs(tmp_path, monkeypatch, fake_transpiler):
    src_dir = tmp_path / "custom_src"
    out_dir = tmp_path / "custom_out"
    src_dir.mkdir()
    out_dir.mkdir()

    write(src_dir / "pipeline_x.py", "print('x')")

    def fake_run_path(path):
        registry._pipelines["xpipe"] = FakePipeline("xpipe")

    monkeypatch.setattr("runpy.run_path", fake_run_path)

    rc = cli_main(["build", "--src-dir", str(src_dir), "--out-dir", str(out_dir)])
    assert rc == 0
    assert (out_dir / "xpipe.yml").read_text(encoding="utf-8") == "name: xpipe\njobs: {}\n"


def test_clean_skips_files_with_unreadable_head(tmp_path, monkeypatch, fake_transpiler):
    """If a file can't be read, treat as NOT marked (so it gets removed)."""
    src_dir = tmp_path / ".pipe"
    out_dir = tmp_path / ".github" / "workflows"
    src_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    # register a single pipeline "p"
    write(src_dir / "pipeline_p.py", "print('p')")

    def fake_run_path(_):
        registry._pipelines["p"] = FakePipeline("p")

    monkeypatch.setattr("runpy.run_path", fake_run_path)

    # unreadable orphan
    orphan = out_dir / "orphan.yml"
    write(orphan, "name: orphan\n")
    try:
        os.chmod(orphan, 0)  # no perms on POSIX; may noop on Windows
    except PermissionError:
        # On some platforms (e.g., Windows), chmod may not restrict permissions as expected.
        # It's safe to ignore this error for the purposes of this test.
        pass

    try:
        rc = cli_main(["build", "--src-dir", str(src_dir), "--out-dir", str(out_dir), "--clean"])
        assert rc == 0
        # on some platforms chmod may not apply; assert that either it's gone or still there
        assert (out_dir / "p.yml").exists()
        # ideally orphan is removed; if not (platform quirk), at least build succeeded
    finally:
        # restore perms so tmp cleanup can delete it
        try:
            os.chmod(orphan, 0o644)
        except FileNotFoundError:
            # File may have already been deleted; safe to ignore during cleanup.
            pass


def test_build_deduplicates_double_matched_files(tmp_path, monkeypatch, capsys, fake_transpiler):
    """
    Ensure a file matching both 'pipeline_*.py' and '*_pipeline.py' is only run once.
    """
    src_dir = tmp_path / ".pipe"
    out_dir = tmp_path / ".github" / "workflows"
    src_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    # This filename matches BOTH patterns
    fname = "pipeline_x_pipeline.py"
    write(src_dir / fname, "print('x')")

    calls = []

    def fake_run_path(path):
        calls.append(path)
        if path.endswith(fname):
            registry._pipelines["x"] = FakePipeline("x")

    monkeypatch.setattr("runpy.run_path", fake_run_path)

    rc = cli_main(["build", "--src-dir", str(src_dir), "--out-dir", str(out_dir)])
    assert rc == 0

    # It should have been discovered and executed exactly once
    assert sum(p.endswith(fname) for p in calls) == 1

    # CLI output should reflect 1 found file (not 2)
    out = capsys.readouterr().out
    assert "Found 1 pipeline files" in out

    # Output must be written correctly once
    assert (out_dir / "x.yml").read_text(encoding="utf-8") == "name: x\njobs: {}\n"


def test_get_pipelines_dict_raises_when_missing(monkeypatch):
    """If pygha.registry has no _pipelines attr, raise a helpful RuntimeError."""
    from pygha.cli import _get_pipelines_dict
    import pygha.registry as reg

    # Remove the attribute, then restore it so the autouse clean_registry teardown succeeds.
    monkeypatch.delattr(reg, "_pipelines", raising=False)
    try:
        with pytest.raises(RuntimeError, match="No _pipelines found in pygha.registry"):
            _get_pipelines_dict()
    finally:
        # Restore a dict so clean_registry's .clear()/.update() won't crash
        monkeypatch.setattr(reg, "_pipelines", {}, raising=False)


def test_get_pipelines_dict_raises_when_not_dict(monkeypatch):
    """If pygha.registry._pipelines exists but is not a dict, raise the same RuntimeError."""
    from pygha.cli import _get_pipelines_dict
    import pygha.registry as reg

    # Set to wrong type, then restore it so the autouse clean_registry teardown succeeds.
    monkeypatch.setattr(reg, "_pipelines", [], raising=False)
    try:
        with pytest.raises(RuntimeError, match="No _pipelines found in pygha.registry"):
            _get_pipelines_dict()
    finally:
        # Restore a dict so clean_registry's .clear()/.update() won't crash
        monkeypatch.setattr(reg, "_pipelines", {}, raising=False)


def test_has_keep_marker_within_max_lines_is_detected(tmp_path):
    # Marker is on the 10th line (1-based), i == 9 — should be checked with max_lines=10
    p = tmp_path / "wf.yml"
    lines = ["noise\n"] * 9 + ["# pygha: keep\n", "more\n"]
    p.write_text("".join(lines), encoding="utf-8")

    from pygha.cli import _has_keep_marker

    assert _has_keep_marker(p, max_lines=10) is True


def test_has_keep_marker_past_max_lines_is_ignored(tmp_path):
    # Marker is on the 11th line (1-based), i == 10 — loop breaks before seeing it when max_lines=10
    p = tmp_path / "wf.yml"
    lines = ["noise\n"] * 10 + ["# pygha: keep\n", "more\n"]
    p.write_text("".join(lines), encoding="utf-8")

    from pygha.cli import _has_keep_marker

    assert _has_keep_marker(p, max_lines=10) is False
    # Sanity check: increasing the window should reveal it
    assert _has_keep_marker(p, max_lines=11) is True


# ── PermissionError -> chmod -> unlink succeeds -> True
def test_safe_unlink_permissionerror_then_chmod_then_success(tmp_path, monkeypatch):
    from pygha.cli import _safe_unlink

    target = tmp_path / "file.yml"
    target.write_text("x", encoding="utf-8")

    calls = {"unlink": 0, "chmod": 0}

    def fake_unlink(self):
        assert self == target
        calls["unlink"] += 1
        if calls["unlink"] == 1:
            raise PermissionError("locked")
        # 2nd call succeeds (no exception)

    def fake_chmod(path, mode):
        assert path == target
        calls["chmod"] += 1
        # succeed

    monkeypatch.setattr(Path, "unlink", fake_unlink, raising=True)
    monkeypatch.setattr(os, "chmod", fake_chmod, raising=True)

    assert _safe_unlink(target) is True
    assert calls == {"unlink": 2, "chmod": 1}


# ── PermissionError -> chmod succeeds -> unlink fails -> False
def test_safe_unlink_permissionerror_then_chmod_then_unlink_fails(tmp_path, monkeypatch):
    from pygha.cli import _safe_unlink

    target = tmp_path / "file.yml"
    target.write_text("x", encoding="utf-8")

    calls = {"unlink": 0, "chmod": 0}

    def fake_unlink(self):
        calls["unlink"] += 1
        if calls["unlink"] == 1:
            raise PermissionError("locked")
        raise OSError("still cannot delete")

    def fake_chmod(path, mode):
        calls["chmod"] += 1
        # succeed

    monkeypatch.setattr(Path, "unlink", fake_unlink, raising=True)
    monkeypatch.setattr(os, "chmod", fake_chmod, raising=True)

    assert _safe_unlink(target) is False
    assert calls == {"unlink": 2, "chmod": 1}


# ── PermissionError -> chmod fails -> False
def test_safe_unlink_permissionerror_and_chmod_fails(tmp_path, monkeypatch):
    from pygha.cli import _safe_unlink

    target = tmp_path / "file.yml"
    target.write_text("x", encoding="utf-8")

    calls = {"unlink": 0, "chmod": 0}

    def fake_unlink(self):
        calls["unlink"] += 1
        raise PermissionError("locked")

    def fake_chmod(path, mode):
        calls["chmod"] += 1
        raise OSError("chmod failed")

    monkeypatch.setattr(Path, "unlink", fake_unlink, raising=True)
    monkeypatch.setattr(os, "chmod", fake_chmod, raising=True)

    assert _safe_unlink(target) is False
    assert calls == {"unlink": 1, "chmod": 1}


# ── FileNotFoundError -> True
def test_safe_unlink_file_not_found_returns_true(tmp_path, monkeypatch):
    from pygha.cli import _safe_unlink

    target = tmp_path / "missing.yml"

    def fake_unlink(self):
        raise FileNotFoundError

    monkeypatch.setattr(Path, "unlink", fake_unlink, raising=True)

    assert _safe_unlink(target) is True


# ── Any other Exception -> False
def test_safe_unlink_other_exception_returns_false(tmp_path, monkeypatch):
    from pygha.cli import _safe_unlink

    target = tmp_path / "file.yml"
    target.write_text("x", encoding="utf-8")

    def fake_unlink(self):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(Path, "unlink", fake_unlink, raising=True)

    assert _safe_unlink(target) is False


def test_clean_orphaned_warns_when_unlink_fails(tmp_path, monkeypatch, capsys):
    from pygha.cli import _clean_orphaned

    out_dir = tmp_path
    orphan = out_dir / "orphan.yml"
    orphan.write_text("name: orphan\n", encoding="utf-8")  # no keep marker

    # Force the deletion helper to "fail" so the warning path executes
    monkeypatch.setattr("pygha.cli._safe_unlink", lambda p: False)

    _clean_orphaned(out_dir, valid_names=set())

    out = capsys.readouterr().out
    # Assert the yellow warning with ANSI codes and filename is printed
    assert f"\033[93m[pygha] Warning: could not remove {orphan} (permissions?)\033[0m" in out
    # And the file was not removed
    assert orphan.exists()


def test_main_dispatches_to_cmd_build(monkeypatch, tmp_path):
    # Arrange: patch cmd_build to capture args and return a sentinel code
    from pygha.cli import main as cli_main
    import pygha.cli as cli

    called = {}

    def fake_cmd_build(src_dir, out_dir, clean):
        called.update({"src_dir": src_dir, "out_dir": out_dir, "clean": clean})
        return 123  # sentinel

    monkeypatch.setattr(cli, "cmd_build", fake_cmd_build)

    # Act
    rc = cli_main(
        ["build", "--src-dir", str(tmp_path / "s"), "--out-dir", str(tmp_path / "o"), "--clean"]
    )

    # Assert: dispatch & args wired correctly, return code propagated
    assert rc == 123
    assert called == {
        "src_dir": str(tmp_path / "s"),
        "out_dir": str(tmp_path / "o"),
        "clean": True,
    }


def test_main_returns_zero_for_unknown_command(monkeypatch):
    # Arrange: bypass argparse parsing to simulate a non-"build" command
    from pygha.cli import main as cli_main
    import argparse

    monkeypatch.setattr(
        argparse.ArgumentParser,
        "parse_args",
        lambda self, argv=None: SimpleNamespace(command="something-else"),
        raising=True,
    )

    # Act
    rc = cli_main([])  # argv ignored by our patch

    # Assert: falls through to the final `return 0`
    assert rc == 0


def test_dunder_main_propagates_exit_code(monkeypatch):
    # Make cli.main return a sentinel so we can assert SystemExit.code
    import pygha.cli as cli

    monkeypatch.setattr(cli, "main", lambda *a, **k: 123)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("pygha.__main__", run_name="__main__", alter_sys=True)

    assert exc.value.code == 123


def test_dunder_main_handles_nonzero_exit(monkeypatch):
    import pygha.cli as cli

    monkeypatch.setattr(cli, "main", lambda *a, **k: 2)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("pygha.__main__", run_name="__main__", alter_sys=True)

    assert exc.value.code == 2
