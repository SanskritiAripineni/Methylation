"""Rebuild the static site and update the live GitHub Pages branch.

    python deploy_gh_pages.py             # show what would happen
    python deploy_gh_pages.py --push      # actually publish

Publishing is opt-in. Without --push this prints the plan and stops, because
`--push` sends content to a URL anyone with the link can read.

It works on a throwaway clone in a temp directory, so your working tree and
whatever branch you are on are never touched.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
BRANCH = "gh-pages"
REMOTE = "https://github.com/SanskritiAripineni/Methylation.git"
LIVE_URL = "https://sanskritiaripineni.github.io/Methylation/"


def run(cmd, cwd, quiet=False):
    result = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if result.returncode != 0:
        sys.exit("failed: %s\n%s%s" % (" ".join(cmd), result.stdout, result.stderr))
    if not quiet and result.stdout.strip():
        print("   " + result.stdout.strip().splitlines()[-1])
    return result.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--push", action="store_true", help="publish for real")
    ap.add_argument("--message", default="Update published results")
    args = ap.parse_args()

    print("1. building the static bundle")
    run([sys.executable, str(ROOT / "publish.py")], REPO, quiet=True)
    site = ROOT / "publish"
    files = [p for p in site.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print("   %d files, %.1f MB" % (len(files), size / 1e6))

    if not args.push:
        print("\n2. would replace the '%s' branch on %s" % (BRANCH, REMOTE))
        print("   and the live site at %s" % LIVE_URL)
        print("\nThat site is PUBLIC - anyone with the link can read it.")
        print("Re-run with --push when you are ready.")
        return

    tmp = Path(tempfile.mkdtemp(prefix="ghpages-"))
    try:
        print("2. preparing a clean branch in %s" % tmp)
        run(["git", "clone", "-q", "--no-local", REMOTE, str(tmp)], REPO, quiet=True)
        run(["git", "checkout", "-q", "--orphan", BRANCH], tmp, quiet=True)
        run(["git", "rm", "-rq", "--cached", "."], tmp, quiet=True)
        for child in tmp.iterdir():
            if child.name == ".git":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()

        shutil.copytree(site, tmp, dirs_exist_ok=True)
        for extra in ("netlify.toml", "vercel.json", "README.md"):
            (tmp / extra).unlink(missing_ok=True)
        # Serve the files as they are instead of running them through Jekyll.
        (tmp / ".nojekyll").touch()

        print("3. publishing")
        run(["git", "add", "-A"], tmp, quiet=True)
        run(["git", "-c", "user.name=publish", "-c", "user.email=noreply@localhost",
             "commit", "-q", "-m", args.message], tmp, quiet=True)
        run(["git", "push", "-q", "--force", "origin", BRANCH], tmp, quiet=True)
        print("   done - live in a minute or two at %s" % LIVE_URL)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
