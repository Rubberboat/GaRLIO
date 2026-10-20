#!/usr/bin/env python3
"""Identify the GaRLIO package actually selected by ROS, including local fork edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

GARLIO_METHODS = ("garlio", "garlio_gpt")
PACKAGE_INPUTS = ("CMakeLists.txt", "package.xml", "LICENSE",
                  "src", "include", "config", "launch", "rviz_cfg")


def fingerprint(package):
    """Hash the same package inputs copied into the fork Docker build."""
    files = {}
    for name in PACKAGE_INPUTS:
        path = package / name
        if not path.exists():
            raise RuntimeError("Missing GaRLIO package input: " + str(path))
        for file in sorted(path.rglob("*")) if path.is_dir() else [path]:
            if file.is_symlink():
                raise RuntimeError("GaRLIO source snapshot must not contain symlinks: " + str(file))
            if file.is_file():
                files[file.relative_to(package).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    payload = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return {"tree_sha256": hashlib.sha256(payload).hexdigest(), "files": files}


def runtime_source(method, image_root=Path("/opt/research"), checkout=None):
    """Refuse an incorrectly sourced overlay or a stale fork build before replay."""
    if method not in GARLIO_METHODS:
        return None
    workspace = "fork_ws" if method == "garlio_gpt" else "catkin_ws"
    expected = (image_root / workspace / "src/garlio").resolve()
    actual = Path(subprocess.check_output(["rospack", "find", "garlio"], text=True).strip()).resolve()
    if actual != expected:
        kind = "garlio_gpt" if method == "garlio_gpt" else "ros"
        raise RuntimeError(
            f"{method} requires {expected}, but ROS selected {actual}. "
            f"Use docker/run.sh {kind} to select the correct environment.")
    if method == "garlio":
        lock = json.loads((image_root / "sources.lock.json").read_text())["sources"]
        source = next(item for item in lock if item["name"] == "GaRLIO")
        head = subprocess.check_output(["git", "-C", str(actual), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(
            ["git", "-C", str(actual), "status", "--porcelain", "--untracked-files=all"], text=True).strip()
        if head != source["commit"] or dirty:
            raise RuntimeError("The pinned GaRLIO baseline was modified; rebuild the image.")
        return {"role": "upstream_baseline", "package_path": str(actual),
                "git_commit": head, "url": source["url"]}
    manifest = json.loads((image_root / "fork-source-manifest.json").read_text())
    built = fingerprint(actual)
    if built != {key: manifest[key] for key in ("tree_sha256", "files")}:
        raise RuntimeError("The built GaRLIO fork source changed; rebuild the image.")
    if checkout is None and os.environ.get("RESEARCH_FORK_SOURCE"):
        checkout = Path(os.environ["RESEARCH_FORK_SOURCE"])
    if checkout is not None and fingerprint(checkout) != built:
        raise RuntimeError("Local GaRLIO source differs from the compiled fork; rebuild the ROS image.")
    return dict(manifest, role="fork", package_path=str(actual), checkout_verified=checkout is not None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    manifest = dict(fingerprint(args.package), git_commit=args.commit,
                    url="https://github.com/Rubberboat/GaRLIO.git")
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
