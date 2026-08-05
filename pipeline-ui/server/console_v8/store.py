"""Where finished runs live, and whether that place survives a restart.

V7 writes every run to `pipeline-ui/runs/`, which is gitignored and sits on the
container's own filesystem. On a free Render instance that filesystem is
rebuilt whenever the service redeploys or wakes from a sleep, so the run list
resets on its own — a run started on Tuesday is gone on Wednesday, and nobody
touched anything. `restore_saved_sample_run()` puts the bundled demonstration
run back, which is why the list looks *almost* right and is missing exactly the
runs a person started themselves.

Two things follow from that, and this module does both:

  1. If a durable directory is configured, put the runs there instead. One
     env var (`METHYLATION_DATA_DIR`) or a mounted disk is enough — attach a
     Render disk, point this at it, and history stops resetting.

  2. If there is no durable directory, say so out loud. The interface asks
     `/api/v8/storage` and prints the answer. Losing a run is bad; losing one
     while the screen implies it was saved is worse.

Nothing here changes how a run is produced or read. It moves one directory and
tells the truth about it.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

# Directories a host may have mounted for us, tried in order. The first that
# exists and is writable wins. `/var/data` is Render's documented default mount
# point for a persistent disk; the others cover Fly and Railway conventions.
MOUNT_CANDIDATES = ("/var/data", "/data", "/mnt/data")

# Set by activate(); read by describe().
_STATE = {
    "path": None,
    "durable": False,
    "reason": "not resolved yet",
    "source": "default",
    "migrated": 0,
}


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolve(default_dir: Path):
    """Pick the runs directory. Returns (path, durable, reason, source)."""
    configured = os.environ.get("METHYLATION_DATA_DIR", "").strip()
    if configured:
        path = Path(configured).expanduser() / "runs"
        if _writable(path):
            return path, True, (
                "Runs are stored in METHYLATION_DATA_DIR (%s) and survive a restart."
                % configured), "env"
        # A configured path that cannot be written to is a deployment mistake,
        # not a reason to silently fall back and lose runs later.
        return (Path(default_dir), False,
                "METHYLATION_DATA_DIR is set to %s but that path cannot be written to, so "
                "runs are being kept on the container's own disk and will be lost when it "
                "restarts." % configured, "env-broken")

    for mount in MOUNT_CANDIDATES:
        mount_path = Path(mount)
        if mount_path.is_dir() and _writable(mount_path / "methylation-runs"):
            return mount_path / "methylation-runs", True, (
                "Runs are stored on the disk mounted at %s and survive a restart." % mount), "mount"

    return (Path(default_dir), False,
            "Runs are stored on this instance's own filesystem. On a host that rebuilds that "
            "filesystem — a free Render instance does, on every redeploy and after it sleeps — "
            "runs you start will disappear. Set METHYLATION_DATA_DIR to a mounted disk to keep "
            "them.", "default")


def _migrate(old_dir: Path, new_dir: Path) -> int:
    """Copy runs already on the ephemeral disk into the durable one, once.

    Only runs that finished (they have a run_record.json) are worth moving, and
    an id already present in the durable directory is never overwritten.
    """
    if not old_dir.is_dir() or old_dir.resolve() == new_dir.resolve():
        return 0
    moved = 0
    new_dir.mkdir(parents=True, exist_ok=True)
    for entry in old_dir.iterdir():
        if not entry.is_dir() or not (entry / "run_record.json").is_file():
            continue
        target = new_dir / entry.name
        if target.exists():
            continue
        try:
            shutil.copytree(entry, target)
            moved += 1
        except OSError:
            continue
    legacy_history = old_dir / "history_v2.jsonl"
    new_history = new_dir / "history_v2.jsonl"
    if legacy_history.is_file() and not new_history.is_file():
        try:
            shutil.copy2(legacy_history, new_history)
        except OSError:
            pass
    return moved


def activate(runner, runs_mod):
    """Point the engine at the resolved directory. Call once, before serving.

    `runner.RUNS_DIR` is read at call time by everything that lists, writes or
    reads back a run, so reassigning it here is enough. `runs_mod.HISTORY` is
    the one exception — it is computed at import — so it is reassigned too.
    """
    default_dir = Path(runner.RUNS_DIR)
    path, durable, reason, source = resolve(default_dir)
    path.mkdir(parents=True, exist_ok=True)

    migrated = _migrate(default_dir, path) if durable else 0

    runner.RUNS_DIR = path
    runs_mod.HISTORY = path / "history_v2.jsonl"

    _STATE.update({"path": str(path), "durable": durable, "reason": reason,
                   "source": source, "migrated": migrated})
    return dict(_STATE)


def describe():
    """What the interface shows in the Runs tab."""
    state = dict(_STATE)
    state["headline"] = ("Runs are saved and survive a restart."
                         if state["durable"] else
                         "Runs on this instance are temporary.")
    return state
