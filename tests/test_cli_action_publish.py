import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from git_ship.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_is_offline_and_reproducible(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("demo attempted network access")

    monkeypatch.setattr("git_ship.github.urlopen", forbidden)
    monkeypatch.setenv("GITHUB_TOKEN", "never-write-this-token")
    args = [
        "render",
        "--demo",
        "--scale",
        "1",
        "--duration",
        "2",
        "--output-dir",
        str(tmp_path),
        "--preview",
        "--cache-profile",
        str(tmp_path / "profile.json"),
    ]
    assert main(args) == 0
    assert (tmp_path / "preview.html").exists()
    assert "never-write-this-token" not in (tmp_path / "profile.json").read_text()
    assert (
        main(
            [
                "render",
                "--profile",
                str(tmp_path / "profile.json"),
                "--duration",
                "2",
                "--output-dir",
                str(tmp_path / "cached"),
            ]
        )
        == 0
    )
    for file in ("git-ship.gif", "git-ship.png", "report.json"):
        assert (tmp_path / file).is_file()


def test_cli_errors_are_actionable(tmp_path, capsys):
    assert main(["render"]) == 1
    assert "requires --username" in capsys.readouterr().err
    assert main(["render", "--demo", "--ships", "1000"]) == 1
    assert "ships" in capsys.readouterr().err
    assert main(["render", "--profile", str(tmp_path / "absent.json")]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_installed_entry_point_and_module(tmp_path):
    for command in (
        [sys.executable, "-m", "git_ship"],
        [str(Path(sys.executable).with_name("git-ship"))],
    ):
        proc = subprocess.run(
            [
                *command,
                "render",
                "--demo",
                "--duration",
                "2",
                "--scale",
                "1",
                "--output-dir",
                str(tmp_path),
            ],
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["frames"] == 20


def test_actual_action_entrypoint_and_outputs(tmp_path):
    env = {
        **os.environ,
        "GITHUB_WORKSPACE": str(tmp_path),
        "SHIP_OUTPUT_DIR": "fleet",
        "SHIP_DEMO": "true",
        "SHIP_DATA_WINDOW": "day",
        "SHIP_CONFIG": "",
        "SHIP_USERNAME": "",
        "GITHUB_TOKEN": "",
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "SHIP_REPOSITORY_OWNER": "sailor",
    }
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["activity_window_days"] == 1
    assert all(language["cargo"] == 0 for language in report["languages"])
    outputs = dict(line.split("=", 1) for line in (tmp_path / "outputs").read_text().splitlines())
    assert Path(outputs["gif"]).is_file() and Path(outputs["png"]).is_file()
    assert Path(outputs["publish-script"]).name == "publish_assets.py"
    env["SHIP_OUTPUT_DIR"] = "../escape"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1 and "subdirectory" in proc.stderr


def test_publisher_changes_only_assets_and_skips_unchanged(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "publish_assets", ROOT / "scripts/publish_assets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    remote, work, assets = (tmp_path / name for name in ("remote.git", "work", "assets"))
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    work.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=work, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    (work / "README.md").write_text("default branch must stay untouched")
    git("add", "README.md")
    git("commit", "-m", "Initial")
    git("remote", "add", "origin", str(remote))
    git("push", "origin", "main")
    before = git("rev-parse", "HEAD")
    assets.mkdir()
    for name in module.ASSETS:
        (assets / name).write_bytes(b"fixture")
    (assets / "unrelated.txt").write_text("never publish this")
    assert module.publish(assets, str(remote), "main") is True
    assert module.publish(assets, str(remote), "main") is False
    git("fetch", "origin", "output")
    assert set(git("ls-tree", "--name-only", "origin/output").splitlines()) == set(module.ASSETS)
    assert git("rev-parse", "main") == before
    # An existing unrelated output-branch file survives the next refresh.
    git("checkout", "-b", "output", "origin/output")
    (work / "keep.txt").write_text("keep")
    git("add", "keep.txt")
    git("commit", "-m", "Unrelated output file")
    git("push", "origin", "output")
    (assets / "git-ship.gif").write_bytes(b"changed fixture")
    assert module.publish(assets, str(remote), "main") is True
    git("fetch", "origin", "output")
    assert git("show", "origin/output:keep.txt") == "keep"
    assert git("rev-parse", "main") == before
    with pytest.raises(ValueError, match="default branch"):
        module.publish(assets, str(remote), "output")
