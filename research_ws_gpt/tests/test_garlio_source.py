import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from garlio_source import fingerprint, runtime_source
from prepare_smoke_config import config_for


class ForkSourceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.package = self.root / "fork_ws/src/garlio"
        self.package.mkdir(parents=True)
        for name in ("CMakeLists.txt", "package.xml", "LICENSE"):
            (self.package / name).write_text(name)
        for name in ("src", "include", "config", "launch", "rviz_cfg"):
            (self.package / name).mkdir()
            (self.package / name / "example").write_text(name)
        self.manifest = dict(fingerprint(self.package), git_commit="image-commit", url="fork")
        (self.root / "fork-source-manifest.json").write_text(json.dumps(self.manifest))

    def runtime(self, checkout=None):
        with patch("garlio_source.subprocess.check_output", return_value=str(self.package)):
            return runtime_source("garlio_gpt", self.root, checkout)

    def test_fork_provenance_records_built_files_and_revision(self):
        result = self.runtime(self.package)
        self.assertEqual(result["role"], "fork")
        self.assertEqual(result["git_commit"], "image-commit")
        self.assertEqual(result["tree_sha256"], self.manifest["tree_sha256"])
        self.assertTrue(result["checkout_verified"])

    def test_baseline_cannot_be_labelled_as_fork(self):
        with patch("garlio_source.subprocess.check_output", return_value=str(self.root / "catkin_ws/src/garlio")):
            with self.assertRaisesRegex(RuntimeError, "ROS selected"):
                runtime_source("garlio_gpt", self.root)

    def test_fork_cannot_be_labelled_as_baseline(self):
        with patch("garlio_source.subprocess.check_output", return_value=str(self.package)):
            with self.assertRaisesRegex(RuntimeError, "ROS selected"):
                runtime_source("garlio", self.root)

    def test_baseline_records_verified_pinned_commit(self):
        baseline = self.root / "catkin_ws/src/garlio"
        (self.root / "sources.lock.json").write_text(json.dumps({
            "sources": [{"name": "GaRLIO", "commit": "pinned", "url": "upstream"}]}))
        with patch("garlio_source.subprocess.check_output", side_effect=[str(baseline), "pinned\n", ""]):
            result = runtime_source("garlio", self.root)
        self.assertEqual(result["role"], "upstream_baseline")
        self.assertEqual(result["git_commit"], "pinned")

    def test_changed_baseline_is_rejected(self):
        baseline = self.root / "catkin_ws/src/garlio"
        (self.root / "sources.lock.json").write_text(json.dumps({
            "sources": [{"name": "GaRLIO", "commit": "pinned", "url": "upstream"}]}))
        for head, status in (("other", ""), ("pinned", " M src/example")):
            with self.subTest(head=head, status=status):
                with patch("garlio_source.subprocess.check_output", side_effect=[str(baseline), head, status]):
                    with self.assertRaisesRegex(RuntimeError, "baseline was modified"):
                        runtime_source("garlio", self.root)

    def test_changed_compiled_source_is_rejected(self):
        (self.package / "src/example").write_text("changed after build")
        with self.assertRaisesRegex(RuntimeError, "built GaRLIO fork source changed"):
            self.runtime()

    def test_local_edits_require_rebuild_but_docs_do_not(self):
        checkout = self.root / "checkout"
        shutil.copytree(self.package, checkout)
        (checkout / "README.md").write_text("Documentation update")
        self.assertTrue(self.runtime(checkout)["checkout_verified"])
        (checkout / "src/new_module.cpp").write_text("new implementation")
        with self.assertRaisesRegex(RuntimeError, "differs from the compiled fork"):
            self.runtime(checkout)

    def test_source_fingerprint_is_independent_of_checkout_location(self):
        checkout = self.root / "checkout"
        shutil.copytree(self.package, checkout)
        self.assertEqual(fingerprint(checkout), fingerprint(self.package))

    def test_fork_config_comes_from_selected_package(self):
        (self.package / "config/loop2.yaml").write_text("fork_setting: 42\npcd_save: {pcd_save_en: true}\n")
        config = config_for("garlio_gpt", self.package.parent)
        self.assertEqual(config["fork_setting"], 42)
        self.assertIs(config["pcd_save"]["pcd_save_en"], False)


if __name__ == "__main__":
    unittest.main()
