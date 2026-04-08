import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "API"


class ValidatePathTests(unittest.TestCase):
    """Tests for Config.validate_path — the CodeQL sanitizer barrier.

    This function is declared as a sanitizer in .github/codeql/extensions/.
    If its behaviour changes, both this test and that model file must be updated.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(API_DIR))
        from Classes.Base import Config
        cls.Config = Config

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)

    def test_valid_path_returns_absolute(self):
        result = self.Config.validate_path(self.base, "casename")
        self.assertTrue(os.path.isabs(result))
        self.assertTrue(result.startswith(self.base))

    def test_traversal_dotdot_is_blocked(self):
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "../outside")

    def test_traversal_absolute_path_is_blocked(self):
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "/etc/passwd")

    def test_traversal_encoded_dotdot_is_blocked(self):
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "case/../../outside")

    def test_null_byte_is_blocked(self):
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "case\x00evil")

    def test_none_input_is_blocked(self):
        # None resolves to the base dir itself, which is rejected
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, None)

    def test_base_dir_itself_is_blocked(self):
        # Pointing exactly at the base is not a valid case path
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "")

    def test_nested_path_is_allowed(self):
        result = self.Config.validate_path(self.base, os.path.join("case", "res", "run1"))
        self.assertTrue(result.startswith(self.base))


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(API_DIR))
        os.environ.setdefault("MUIOGO_SECRET_KEY", "smoke-test-secret")
        cls.app_module = importlib.import_module("app")
        cls.client = cls.app_module.app.test_client()

    def test_app_import_from_arbitrary_cwd(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(API_DIR)
        env.setdefault("MUIOGO_SECRET_KEY", "smoke-test-secret")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, "-c", "import app; print(app.app.import_name)"],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("app", result.stdout.strip())

    def test_home_route(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", response.data)

    def test_get_session_route(self):
        response = self.client.get("/getSession")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"session": None})

    def test_clear_session_route(self):
        response = self.client.post("/setSession", json={"case": None})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"osycase": None})

    def test_repo_has_no_unmerged_paths(self):
        result = subprocess.run(
            ["git", "ls-files", "-u"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
