import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from record_traj import TumWriter
import run_experiment as runner
from prepare_smoke_config import config_for


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "trajectory.tum"
        self.writer = TumWriter(self.path)
        self.addCleanup(self.writer.close)

    def write(self, sec=1700000000, nsec=123456789, values=None, frame="map"):
        self.writer.write(sec, nsec, values or [1, 2, 3, 0, 0, 0, 1], frame, "imu")

    def test_header_time_nanoseconds_and_tum_order(self):
        self.write()
        self.writer.close()
        self.assertEqual(self.path.read_text(), "1700000000.123456789 1 2 3 0 0 0 1\n")

    def test_duplicate_and_backward_time_are_errors(self):
        self.write()
        for nsec in [123456789, 123456788]:
            with self.assertRaisesRegex(ValueError, "timestamp"):
                self.write(nsec=nsec)

    def test_nonfinite_pose_is_error(self):
        with self.assertRaises(ValueError):
            self.write(values=[float("nan"), 0, 0, 0, 0, 0, 1])

    def test_invalid_quaternion_is_error(self):
        with self.assertRaisesRegex(ValueError, "Quaternion"):
            self.write(values=[0, 0, 0, 0, 0, 0, 0])

    def test_frame_change_is_error(self):
        self.write()
        with self.assertRaisesRegex(ValueError, "frame"):
            self.write(sec=1700000001, frame="other")

    def test_zero_time_is_error(self):
        with self.assertRaises(ValueError):
            self.write(sec=0, nsec=0)

    def test_existing_trajectory_is_never_overwritten(self):
        with self.assertRaises(FileExistsError):
            TumWriter(self.path)


class ConfigurationTests(unittest.TestCase):
    def test_launch_defaults_are_not_lost_and_pcd_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Point-LIO/config").mkdir(parents=True)
            (root / "Point-LIO/launch").mkdir()
            (root / "Point-LIO/config/horizon.yaml").write_text("init_map_size: 100\npcd_save: {pcd_save_en: true}\n")
            (root / "Point-LIO/launch/mapping_horizon.launch").write_text(
                '<launch><node><param name="init_map_size" type="int" value="10"/>'
                '<param name="use_imu_as_input" type="bool" value="0"/></node></launch>')
            config = config_for("point_lio", root)
            self.assertEqual(config["init_map_size"], 10)
            self.assertIs(config["use_imu_as_input"], False)
            self.assertIs(config["pcd_save"]["pcd_save_en"], False)

    def test_private_namespace_for_point_lio_only(self):
        import xml.etree.ElementTree as ET
        root = Path(__file__).resolve().parents[1] / "launch"
        point = ET.parse(root / "point_lio.launch").getroot()
        self.assertIsNotNone(point.find("node/rosparam"))
        for method in ("fast_lio", "garlio"):
            self.assertIsNotNone(ET.parse(root / (method + ".launch")).getroot().find("rosparam"))


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.config = {"common": {"lid_topic": "/lidar", "radar_topic": "/radar"}}
        self.inputs = {"topics": {"/lidar": {"first_header_ns": 10**9, "last_header_ns": 10*10**9},
                                  "/radar": {"first_header_ns": 10**9, "last_header_ns": 9*10**9}}}
        self.output = {"poses": 10, "first_stamp_ns": 2*10**9, "last_stamp_ns": 9*10**9, "error": None}

    def test_tail_compares_to_correct_sensor(self):
        a = runner.validate_coverage(self.output, self.inputs, self.config, "point_lio", 2)
        b = runner.validate_coverage(self.output, self.inputs, self.config, "garlio", 2)
        c = runner.validate_coverage(self.output, self.inputs, self.config, "garlio_gpt", 2)
        self.assertEqual(a["tail_lag_seconds"], 1)
        self.assertEqual(b["tail_lag_seconds"], 0)
        self.assertEqual(c["tail_lag_seconds"], 0)

    def test_early_stall_fails_even_with_many_poses(self):
        self.output["last_stamp_ns"] = 3*10**9
        with self.assertRaisesRegex(RuntimeError, "tail lag"):
            runner.validate_coverage(self.output, self.inputs, self.config, "point_lio", 2)

    def test_recorder_error_is_not_success(self):
        self.output["error"] = "Disk full"
        with self.assertRaisesRegex(RuntimeError, "Disk full"):
            runner.validate_coverage(self.output, self.inputs, self.config, "point_lio", 2)


class PreflightTests(unittest.TestCase):
    def inspect(self, method="garlio", radar=True, duplicate=False, wrong_type=False):
        types_ = {"/lidar": "livox_ros_driver/CustomMsg", "/imu": "sensor_msgs/Imu"}
        if radar:
            types_["/radar"] = "sensor_msgs/PointCloud"
        if wrong_type:
            types_["/lidar"] = "sensor_msgs/PointCloud2"

        class Bag:
            def __init__(self, path): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def get_start_time(self): return 1.0
            def get_end_time(self): return 5.0
            def get_type_and_topic_info(self):
                return types.SimpleNamespace(topics={key: types.SimpleNamespace(msg_type=value, message_count=2) for key, value in types_.items()})
            def read_messages(self, topics, start_time, end_time):
                for topic in topics:
                    for nsec in (10**9, 10**9 if duplicate else 2*10**9):
                        msg = types.SimpleNamespace(header=types.SimpleNamespace(stamp=types.SimpleNamespace(to_nsec=lambda n=nsec: n)))
                        yield topic, msg, None

        modules = {"rosbag": types.SimpleNamespace(Bag=Bag),
                   "genpy": types.SimpleNamespace(Time=types.SimpleNamespace(from_sec=lambda x: x))}
        config = {"common": {"lid_topic": "/lidar", "imu_topic": "/imu", "radar_topic": "/radar"},
                  "preprocess": {"lidar_type": 0 if method in runner.GARLIO_METHODS else 1, "radar_type": 0}}
        with patch.dict(sys.modules, modules):
            return runner.inspect_bag(Path("fake.bag"), method, config, 0, 3)

    def test_missing_radar_fails_before_launch(self):
        with self.assertRaisesRegex(ValueError, "Missing/empty"):
            self.inspect(radar=False)

    def test_point_lio_does_not_require_radar(self):
        self.assertEqual(len(self.inspect(method="point_lio", radar=False)["topics"]), 2)

    def test_fork_requires_radar_and_accepts_garlio_lidar_type(self):
        self.assertEqual(len(self.inspect(method="garlio_gpt")["topics"]), 3)
        with self.assertRaisesRegex(ValueError, "Missing/empty"):
            self.inspect(method="garlio_gpt", radar=False)

    def test_wrong_lidar_message_type_fails(self):
        with self.assertRaisesRegex(ValueError, "expected"):
            self.inspect(wrong_type=True)

    def test_sensor_time_reset_fails(self):
        with self.assertRaisesRegex(ValueError, "timestamp"):
            self.inspect(duplicate=True)


class LifecycleTests(unittest.TestCase):
    def test_failed_master_is_recorded_and_cleaned_up(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "input.yaml"
            config.write_text("common: {lid_topic: /lidar, imu_topic: /imu}\n")
            args = types.SimpleNamespace(config=config, method="point_lio", sequence="cp", rate=0.5,
                                         start=0, duration=30, drain_seconds=0, max_tail_lag=2)
            with patch.object(runner.subprocess, "Popen", side_effect=FileNotFoundError("roscore not installed")):
                with self.assertRaises(FileNotFoundError):
                    runner.run_once(args, root / "run_1", {}, {})
            meta = json.loads((root / "run_1/meta.json").read_text())
            self.assertEqual(meta["status"], "failed")
            self.assertIn("roscore not installed", meta["error"])
            self.assertIn("finished_utc", meta)

    def test_stop_only_terminates_owned_process(self):
        own = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            runner.stop(own)
            self.assertIsNotNone(own.poll())
            self.assertIsNone(other.poll())
        finally:
            runner.stop(own)
            runner.stop(other)


if __name__ == "__main__":
    unittest.main()
