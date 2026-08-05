"""Holds V8's run storage to what it promises.

    python tests/test_v8_storage.py

No test framework - there is none in this project. Exit code 0 means every
check passed.

The check that matters is the last group: `durable` must be False whenever the
runs directory is one the host can rebuild. The interface prints that answer,
and a wrong one is worse than no answer at all - it tells someone their runs
are safe while they are not.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from console_v8 import store                 # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  [pass] %s" % name)
    else:
        print("  [FAIL] %s%s" % (name, ("\n         " + detail) if detail else ""))
        FAILURES.append(name)


class env:
    """Set METHYLATION_DATA_DIR for one block, and put it back afterwards."""

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.old = os.environ.get("METHYLATION_DATA_DIR")
        if self.value is None:
            os.environ.pop("METHYLATION_DATA_DIR", None)
        else:
            os.environ["METHYLATION_DATA_DIR"] = self.value

    def __exit__(self, *_):
        if self.old is None:
            os.environ.pop("METHYLATION_DATA_DIR", None)
        else:
            os.environ["METHYLATION_DATA_DIR"] = self.old


work = Path(tempfile.mkdtemp(prefix="v8-storage-"))
ephemeral = work / "runs"
ephemeral.mkdir(parents=True)

# ---------------------------------------------------------------------------
print("\nwith nowhere durable to write, it says so")
# On a machine that really does have one of the mount points, finding it is
# the correct answer and this group has nothing to say.
mounted = [m for m in store.MOUNT_CANDIDATES if Path(m).is_dir()]
if mounted:
    print("  [skip] %s exists on this machine - durable storage is available here"
          % ", ".join(mounted))
else:
    with env(None):
        path, durable, reason, source = store.resolve(ephemeral)
    check("falls back to the given directory", Path(path) == ephemeral)
    check("does not claim to be durable", durable is False)
    check("names the failure mode in the reason", "disappear" in reason.lower())
    check("reports the source it used", source == "default")

# ---------------------------------------------------------------------------
print("\nwith METHYLATION_DATA_DIR set, runs go there")
durable_root = work / "disk"
with env(str(durable_root)):
    path, durable, reason, source = store.resolve(ephemeral)
check("uses the configured directory", Path(path) == durable_root / "runs")
check("reports durable", durable is True)
check("says where, in the reason", str(durable_root) in reason)
check("reports the source it used", source == "env")

# ---------------------------------------------------------------------------
print("\na configured directory that cannot be written is not silently ignored")
unwritable = work / "readonly"
unwritable.mkdir()
unwritable.chmod(0o500)
try:
    with env(str(unwritable / "nested")):
        path, durable, reason, source = store.resolve(ephemeral)
    check("falls back rather than crashing", Path(path) == ephemeral)
    check("does not claim to be durable", durable is False)
    check("says the configured path was the problem", "METHYLATION_DATA_DIR" in reason)
    check("distinguishes a broken setting from no setting", source == "env-broken")
finally:
    unwritable.chmod(0o700)

# ---------------------------------------------------------------------------
print("\nfinished runs already on the ephemeral disk are carried across")
(ephemeral / "20260101-000000-full-aaaaaa").mkdir(parents=True)
(ephemeral / "20260101-000000-full-aaaaaa" / "run_record.json").write_text("{}", encoding="utf-8")
# A run still in flight has no record yet; there is nothing to carry across.
(ephemeral / "20260102-000000-full-bbbbbb").mkdir(parents=True)
(ephemeral / "history_v2.jsonl").write_text('{"run_id":"x"}\n', encoding="utf-8")

target = work / "disk2" / "runs"
moved = store._migrate(ephemeral, target)
check("moves the finished run", moved == 1)
check("the record came with it",
      (target / "20260101-000000-full-aaaaaa" / "run_record.json").is_file())
check("leaves the unfinished run behind",
      not (target / "20260102-000000-full-bbbbbb").exists())
check("brings the timing history too", (target / "history_v2.jsonl").is_file())
check("running it again copies nothing twice", store._migrate(ephemeral, target) == 0)

# ---------------------------------------------------------------------------
print("\nthe description the interface prints is complete")
with env(None):
    store.resolve(ephemeral)
described = store.describe()
for key in ("path", "durable", "reason", "source", "headline"):
    check("describe() carries %r" % key, key in described)

shutil.rmtree(work, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print("FAILED - %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all checks passed")
