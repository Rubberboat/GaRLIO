#!/usr/bin/env python3
"""Run isolated ROS1 repeats, saving config, provenance, CPU samples and trajectories."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import threading
import time
import xmlrpc.client
from garlio_source import GARLIO_METHODS, runtime_source

ROOT = Path(__file__).resolve().parents[1]
ODOMETRY = {"point_lio": "/aft_mapped_to_init", "fast_lio": "/Odometry",
            "garlio": "/aft_mapped_to_init", "garlio_gpt": "/aft_mapped_to_init"}
NODES = {"point_lio": ["/laserMapping"], "fast_lio": ["/laserMapping"],
         "garlio": ["/pointProcess", "/lidarMapping"], "garlio_gpt": ["/pointProcess", "/lidarMapping"]}


def save_json(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def inspect_bag(path, method, config, start, duration):
    """Stream header times; check required inputs within the requested playback window."""
    import rosbag
    lidar_type = config["preprocess"]["lidar_type"]
    hesai = method in GARLIO_METHODS and lidar_type == 1
    if not hesai and lidar_type != (0 if method in GARLIO_METHODS else 1):
        raise ValueError("Supported inputs: Livox Horizon; GaRLIO also supports Hesai PointCloud2")
    topics = {config["common"]["lid_topic"]: ("sensor_msgs/PointCloud2" if hesai else "livox_ros_driver/CustomMsg"),
              config["common"]["imu_topic"]: "sensor_msgs/Imu"}
    if method in GARLIO_METHODS:
        radar_type = config["preprocess"]["radar_type"]
        if radar_type not in (0, 1):
            raise ValueError("Unsupported radar_type")
        topics[config["common"]["radar_topic"]] = ("sensor_msgs/PointCloud", "sensor_msgs/PointCloud2")[radar_type]
    if len(topics) != (3 if method in GARLIO_METHODS else 2):
        raise ValueError("Input topic names must be distinct")
    if any(not name.startswith("/") for name in topics):
        raise ValueError("Use absolute input topic names")
    with rosbag.Bag(str(path)) as bag:
        available = bag.get_type_and_topic_info().topics
        for topic, expected in topics.items():
            if topic not in available or available[topic].message_count == 0:
                raise ValueError("Missing/empty required topic: " + topic)
            if available[topic].msg_type != expected:
                raise ValueError(f"{topic}: expected {expected}, got {available[topic].msg_type}")
        begin = bag.get_start_time() + start
        end = min(bag.get_end_time(), begin + duration) if duration is not None else bag.get_end_time()
        if begin >= end:
            raise ValueError("Empty playback window")
        import genpy
        stats = {topic: {"count": 0, "first_header_ns": None, "last_header_ns": None} for topic in topics}
        for topic, msg, _ in bag.read_messages(topics=list(topics), start_time=genpy.Time.from_sec(begin), end_time=genpy.Time.from_sec(end)):
            row = stats[topic]
            if hesai and topic == config["common"]["lid_topic"]:
                # Match GaRLIO's registered PCL Hesai point layout, not only the
                # ROS envelope. timestamp is an absolute point time.
                fields = {field.name: (field.datatype, field.count) for field in msg.fields}
                required = {name: (7, 1) for name in ("x", "y", "z", "intensity")}
                required.update(timestamp=(8, 1), ring=(4, 1))
                if any(fields.get(name) != spec for name, spec in required.items()):
                    raise ValueError("Hesai PointCloud2 needs float32 xyz/intensity, float64 timestamp and uint16 ring")
                if msg.width * msg.height == 0:
                    raise ValueError("Empty Hesai PointCloud2 frame")
            stamp = msg.header.stamp.to_nsec()
            if stamp <= 0 or (row["last_header_ns"] is not None and stamp <= row["last_header_ns"]):
                raise ValueError("Zero/non-increasing sensor header timestamp on " + topic)
            if row["first_header_ns"] is None:
                row["first_header_ns"] = stamp
            row["last_header_ns"] = stamp
            row["count"] += 1
        if any(row["count"] < 2 for row in stats.values()):
            raise ValueError("Too few input messages within playback window")
    return {"topics": stats, "record_time_start": begin, "record_time_end": end,
            "duration": end - begin, "types": topics}


def stop(process):
    """Terminate only this runner's process group, including orphaned children."""
    if process is None:
        return
    import psutil
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    for sig, timeout in ((signal.SIGINT, 10), (signal.SIGTERM, 3), (signal.SIGKILL, 2)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            continue
        _, children = psutil.wait_procs(children, timeout=timeout)
        if not children:
            return
    process.poll()


def check_alive(processes):
    for name, process in processes.items():
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited ({process.returncode}); inspect {name}.log")


def wait_for(check, processes, timeout, message):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        check_alive(processes)
        try:
            if check():
                return
        except (OSError, xmlrpc.client.Error):
            pass
        time.sleep(0.2)
    raise RuntimeError(message)


def sample_cpu(launch_pid, path, done):
    import psutil
    tracked = {}
    with path.open("w") as file:
        writer = csv.writer(file)
        writer.writerow(["unix_time", "pid", "process", "cpu_percent_one_core", "rss_bytes"])
        while not done.wait(1.0):
            try:
                root = psutil.Process(launch_pid)
                family = [root] + root.children(recursive=True)
            except psutil.Error:
                break
            for process in family:
                try:
                    key = (process.pid, process.create_time())
                    if key not in tracked:
                        tracked[key] = process
                        process.cpu_percent(None)
                        continue
                    process = tracked[key]
                    writer.writerow([time.time(), process.pid, process.name(), process.cpu_percent(None), process.memory_info().rss])
                except psutil.Error:
                    continue
            file.flush()


def validate_coverage(stats, preflight, config, method, max_tail_lag):
    if stats.get("error") or stats["poses"] < 5:
        raise RuntimeError(stats.get("error") or "Fewer than five output poses")
    source = config["common"]["radar_topic" if method in GARLIO_METHODS else "lid_topic"]
    times = preflight["topics"][source]
    start_lag = (stats["first_stamp_ns"] - times["first_header_ns"]) / 1e9
    tail_lag = (times["last_header_ns"] - stats["last_stamp_ns"]) / 1e9
    if tail_lag > max_tail_lag or tail_lag < -max_tail_lag:
        raise RuntimeError(f"Output tail lag {tail_lag:.3f}s is outside tolerance {max_tail_lag}s")
    return {"start_lag_seconds": start_lag, "tail_lag_seconds": tail_lag}


def run_once(args, run_dir, preflight, provenance):
    import yaml
    run_dir.mkdir(parents=True, exist_ok=False)
    original = args.config.read_text()
    config = yaml.safe_load(original)
    # Give both baseline and fork their own writable trajectory directory.
    if args.method in GARLIO_METHODS:
        config.setdefault("pcd_save", {})["traj_save_path"] = str(run_dir)
    effective = yaml.safe_dump(config, sort_keys=False)
    config_path = run_dir / "config.effective.yaml"
    config_path.write_text(effective)
    (run_dir / "config.requested.yaml").write_text(original)
    meta = dict(provenance, status="running", started_utc=utc_now(), method=args.method,
                sequence=args.sequence, rate=args.rate, start=args.start, duration=args.duration,
                config_requested=original, config_effective=effective, config_sha256=digest(config_path),
                preflight=preflight, commands={}, drain_seconds=args.drain_seconds,
                max_tail_lag_seconds=args.max_tail_lag)
    save_json(run_dir / "meta.json", meta)
    env = os.environ.copy()
    processes, logs = {}, []
    done = threading.Event()
    cpu_thread = None
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(2)

    def start(name, command):
        meta["commands"][name] = command
        log = (run_dir / (name + ".log")).open("w")
        logs.append(log)
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes[name] = process
        return process

    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env.update(ROS_MASTER_URI=f"http://127.0.0.1:{port}", ROS_IP="127.0.0.1",
                   ROS_HOSTNAME="localhost", ROS_LOG_DIR=str(run_dir / "roslog"))
        start("master", ["roscore", "-p", str(port)])
        api = xmlrpc.client.ServerProxy(env["ROS_MASTER_URI"])
        wait_for(lambda: api.getPid("/research_runner")[0] == 1, processes, 30, "ROS master startup timed out")
        api.setParam("/research_runner", "/use_sim_time", True)
        launch_method = "garlio" if args.method in GARLIO_METHODS else args.method
        launch = start("launch", ["roslaunch", str(ROOT / "launch" / (launch_method + ".launch")), "config:=" + str(config_path)])
        start("recorder", [sys.executable, str(ROOT / "scripts/record_traj.py"), "--topic", ODOMETRY[args.method],
                           "--output", str(run_dir / "trajectory.tum"), "--stats", str(run_dir / "recorder.json")])

        def ready():
            code, _, state = api.getSystemState("/research_runner")
            publishers, subscribers = dict(state[0]), dict(state[1])
            sensor_ready = all(subscribers.get(topic) for topic in preflight["topics"])
            odometry_ready = (publishers.get(ODOMETRY[args.method]) and
                              "/trajectory_recorder" in subscribers.get(ODOMETRY[args.method], []))
            internal = args.method not in GARLIO_METHODS or all(subscribers.get(topic) for topic in
                       ("/laser_cloud_surf", "/filtered_points", config["common"].get("topic_outlier_pc2", "/eagle_data/outlier_pc2")))
            return code == 1 and sensor_ready and odometry_ready and internal

        wait_for(ready, processes, 60, "Required sensor/odometry connections were not registered")
        meta["ros_parameters"] = api.getParam("/research_runner", "/")[2]
        save_json(run_dir / "meta.json", meta)
        # Registration alone does not guarantee a live mapper; ping each node as well.
        node_apis = []
        for node in NODES[args.method]:
            code, _, uri = api.lookupNode("/research_runner", node)
            if code != 1:
                raise RuntimeError("Missing node " + node)
            node_apis.append(xmlrpc.client.ServerProxy(uri))

        def healthy():
            check_alive({k: v for k, v in processes.items() if k != "player"})
            for node_api in node_apis:
                if node_api.getPid("/research_runner")[0] != 1:
                    raise RuntimeError("Mapper node stopped responding")

        cpu_thread = threading.Thread(target=sample_cpu, args=(launch.pid, run_dir / "cpu.csv", done), daemon=True)
        cpu_thread.start()
        command = ["rosbag", "play", "--clock", "--rate", str(args.rate), "--delay", "2", "--start", str(args.start)]
        if args.duration is not None:
            command += ["--duration", str(args.duration)]
        command += [str(args.bag), "--topics", *preflight["topics"]]
        meta["replay_started_unix"] = time.time()
        player = start("player", command)
        deadline = time.monotonic() + preflight["duration"] / args.rate + 120
        while player.poll() is None:
            healthy()
            if time.monotonic() > deadline:
                raise RuntimeError("Bag playback exceeded wall-time watchdog")
            time.sleep(0.5)
        if player.returncode != 0:
            raise RuntimeError(f"Bag player failed ({player.returncode})")
        meta["replay_finished_unix"] = time.time()
        deadline = time.monotonic() + args.drain_seconds
        while time.monotonic() < deadline:
            healthy()
            time.sleep(0.2)
        healthy()
        # Flush recorder before consuming stats, while master is still available.
        stop(processes["recorder"])
        if processes["recorder"].returncode != 0:
            raise RuntimeError("Recorder failed or did not shut down cleanly")
        stats = json.loads((run_dir / "recorder.json").read_text())
        meta["recording"] = stats
        meta.update(validate_coverage(stats, preflight, config, args.method, args.max_tail_lag))
        meta["status"] = "completed"
    except BaseException as error:
        meta.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        for name in ("player", "launch", "recorder", "master"):
            stop(processes.get(name))
        done.set()
        if cpu_thread:
            cpu_thread.join(timeout=3)
        meta["exit_codes"] = {name: process.poll() for name, process in processes.items()}
        meta["finished_utc"] = utc_now()
        for log in logs:
            log.close()
        socket.setdefaulttimeout(old_timeout)
        save_json(run_dir / "meta.json", meta)
    print(f"Completed: {run_dir}", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("method", choices=ODOMETRY)
    p.add_argument("sequence")
    p.add_argument("--bag", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path, help="New experiment directory; repeats are method/sequence/run_k")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--rate", type=float, default=0.5)
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--duration", type=float)
    p.add_argument("--drain-seconds", type=float, default=15)
    p.add_argument("--max-tail-lag", type=float, default=2)
    args = p.parse_args()
    numbers = [args.rate, args.start, args.drain_seconds, args.max_tail_lag]
    if args.duration is not None:
        numbers.append(args.duration)
    if (not all(math.isfinite(x) for x in numbers) or args.rate <= 0 or args.runs < 1 or
            args.start < 0 or args.drain_seconds < 0 or args.max_tail_lag < 0 or
            (args.duration is not None and args.duration <= 0)):
        p.error("Invalid rate, repeat count or time limit")
    if not args.sequence or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.sequence):
        p.error("Sequence must be a simple directory label")
    for field in ("bag", "config", "output"):
        setattr(args, field, getattr(args, field).resolve())
    import yaml
    import psutil
    config = yaml.safe_load(args.config.read_text())
    base = args.output / args.method / args.sequence
    if base.exists():
        p.error("Output already exists; use a new experiment ID to avoid overwriting runs")
    selected_source = runtime_source(args.method)
    print("Preflight: reading sensor headers and hashing bag (once for all repeats).", flush=True)
    preflight = inspect_bag(args.bag, args.method, config, args.start, args.duration)
    commit = os.environ.get("RESEARCH_GIT_COMMIT")
    dirty = os.environ.get("RESEARCH_GIT_DIRTY")
    if commit is None:
        try:
            commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
            dirty = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
        except (OSError, subprocess.CalledProcessError):
            commit, dirty = "unknown", "unknown"
    manifest = Path("/opt/research/source-manifest.json")
    if not manifest.exists():
        manifest = ROOT / "source-manifest.json"
    if not manifest.exists():
        raise RuntimeError("No verified source manifest; build the image or bootstrap sources first")
    provenance = {"git_commit": commit, "git_status": dirty,
                  "image_git_commit": os.environ.get("RESEARCH_IMAGE_COMMIT", "unknown"),
                  "upstream_sources": json.loads(manifest.read_text()),
                  "garlio_source": selected_source,
                  "bag": str(args.bag), "bag_sha256": digest(args.bag), "bag_bytes": args.bag.stat().st_size,
                  "machine": {"platform": platform.platform(), "machine": platform.machine(),
                              "processor": platform.processor(), "cpu_logical": os.cpu_count(),
                              "cpu_physical": psutil.cpu_count(logical=False), "ram_bytes": psutil.virtual_memory().total},
                  "harness_sha256": {str(f.relative_to(ROOT)): digest(f)
                                     for folder in ("scripts", "launch") for f in sorted((ROOT / folder).glob("*")) if f.is_file()}}
    for filename in ("build-packages.txt", "build-python.txt"):
        path = Path("/opt/research") / filename
        if path.exists():
            provenance[filename] = path.read_text()
    for run in range(1, args.runs + 1):
        run_once(args, base / f"run_{run}", preflight, provenance)


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Received signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    main()
