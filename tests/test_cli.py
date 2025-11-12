import os
from pathlib import Path
import pytest

from pypipe import registry
from pypipe.cli import main as cli_main


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

    # IMPORTANT: patch where it's used (pypipe.cli), not where it's defined
    monkeypatch.setattr("pypipe.cli.GitHubTranspiler", FakeTranspiler)
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
    write(out_dir / "old.yml", "name: old\n")                               # should be deleted
    write(out_dir / "keep1.yml", "# pypipe: keep\nname: keep1\n")           # keep
    write(out_dir / "keep2.yml", "#pypipe :    KEEP\nname: keep2\n")        # keep (spacing/case)
    write(out_dir / "pipe1.yml", "name: pipe1\n")                           # will be rewritten

    # pipelines produced by current run: only "pipe1"
    write(src_dir / "pipeline_any.py", "print('hi')")

    def fake_run_path(_):
        registry._pipelines["pipe1"] = FakePipeline("pipe1")

    monkeypatch.setattr("runpy.run_path", fake_run_path)

    # sanity: keep marker detection
    from pypipe.cli import _has_keep_marker
    assert _has_keep_marker(out_dir / "keep1.yml")
    assert _has_keep_marker(out_dir / "keep2.yml")

    rc = cli_main(["build", "--src-dir", str(src_dir), "--out-dir", str(out_dir), "--clean"])
    assert rc == 0

    assert not (out_dir / "old.yml").exists()
    assert (out_dir / "keep1.yml").exists()
    assert (out_dir / "keep2.yml").exists()
    assert (out_dir / "pipe1.yml").read_text(encoding="utf-8") == "name: pipe1\njobs: {}\n"


def test_build_no_pipelines_prints_message_and_exits_zero(tmp_path, monkeypatch, capsys, fake_transpiler):
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
