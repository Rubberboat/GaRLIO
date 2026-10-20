#!/usr/bin/env python3
"""Combine original YAML and launch parameters for wiring checks, not accuracy evaluation."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

FILES = {
    "point_lio": ("Point-LIO", "horizon.yaml", "mapping_horizon.launch"),
    "fast_lio": ("FAST_LIO", "horizon.yaml", "mapping_horizon.launch"),
    "garlio": ("garlio", "loop2.yaml", "mapping_loop2.launch"),
    "garlio_gpt": ("garlio", "loop2.yaml", "mapping_loop2.launch"),
}


def config_for(method, sources=None):
    import yaml
    if sources is None:
        workspace = "fork_ws" if method == "garlio_gpt" else "catkin_ws"
        sources = Path("/opt/research") / workspace / "src"
    directory, config, launch = FILES[method]
    base = sources / directory
    data = yaml.safe_load((base / "config" / config).read_text())
    # GaRLIO's launch has no numerical defaults outside YAML.
    if method not in ("garlio", "garlio_gpt"):
        for param in ET.parse(base / "launch" / launch).iter("param"):
            name, value, kind = param.get("name"), param.get("value"), param.get("type")
            converters = {"bool": lambda v: v.lower() in ("true", "1"), "int": int, "double": float}
            data[name] = converters.get(kind, str)(value)
    # Storage-only change shared by all smoke configurations. FAST-LIO's
    # Horizon YAML otherwise accumulates the entire cloud in memory for PCD.
    data.setdefault("pcd_save", {})["pcd_save_en"] = False
    return data


if __name__ == "__main__":
    import yaml
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("method", choices=FILES)
    p.add_argument("--sources", type=Path, help="Override package parent; default follows the selected method")
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    data = config_for(args.method, args.sources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        out.write("# PHASE 0 SMOKE ONLY: upstream calibration, not NTU-verified.\n")
        yaml.safe_dump(data, out, sort_keys=False)
    print("WARNING: Smoke configuration only. Shared NTU calibration must be verified in Phase 1.")
