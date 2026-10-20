#!/usr/bin/env python3
"""Fetch exact upstream commits without changing existing checkouts."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def bootstrap(root, verify_only=False):
    sources = json.loads((root / "sources.lock.json").read_text())["sources"]
    records = []
    for source in sources:
        dest = root / source["path"]
        if not dest.exists():
            if verify_only:
                raise RuntimeError("Missing source: " + str(dest))
            dest.mkdir(parents=True)
            git(dest, "init", "-q")
            git(dest, "remote", "add", "origin", source["url"])
            git(dest, "fetch", "--depth=1", "origin", source["commit"])
            git(dest, "checkout", "--detach", "FETCH_HEAD")
            git(dest, "submodule", "update", "--init", "--recursive")
        head = git(dest, "rev-parse", "HEAD")
        if head != source["commit"]:
            raise RuntimeError(f"Refusing to reset {dest}: expected {source['commit']}, got {head}")
        dirty = git(dest, "status", "--porcelain", "--untracked-files=all")
        submodules = git(dest, "submodule", "status", "--recursive")
        # git() strips leading whitespace, so test the 40-character SHA token too.
        bad_submodules = [line for line in submodules.splitlines()
                          if line.lstrip().startswith(("-", "+", "U"))]
        if dirty or bad_submodules:
            raise RuntimeError(f"Source is modified or has missing/mismatched submodules: {dest}\n{dirty}\n{submodules}")
        records.append(dict(source, verified_commit=head, submodules=submodules))
        print(f"Verified {source['name']}: {head}")
    (root / "source-manifest.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    bootstrap(args.root.resolve(), args.verify_only)
