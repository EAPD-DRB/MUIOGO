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
    """Tests for Config.validate_path — the one containment check in the app.

    Nothing else in API/ decides whether a path is allowed; every other
    realpath() call just builds an absolute path for the solver command line.
    So if a traversal test here is deleted or relaxed, nothing downstream
    catches it.

    The function has to do two jobs at once, and the tests are split to match:
    refuse traversal (TRAVERSAL below) while still allowing a case reached
    through an operator-placed symlink in DataStorage (SYMLINK below), which is
    how the CLEWs-FJI / CLEWs-PHL handoff stores its cases.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(API_DIR))
        from Classes.Base import Config
        cls.Config = Config

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp())
        self.outside = os.path.realpath(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)
        shutil.rmtree(self.outside, ignore_errors=True)

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

    # --- TRAVERSAL: more shapes of the same attack ---

    def test_further_traversal_shapes_are_blocked(self):
        for attempt in ("..", ".", "./", "../", "/", "//etc/passwd",
                        "case/..", "a/../../..", "a/./../../b"):
            with self.subTest(attempt=attempt):
                with self.assertRaises(PermissionError):
                    self.Config.validate_path(self.base, attempt)

    # --- SYMLINK: the operator handoff, and the holes it must not open ---

    def _linked_case(self, name="Philippines_v16"):
        """A case living outside DataStorage, reached by a relative symlink.

        This is what pull-handoff builds: the case is tracked in its own country
        repository and DataStorage only points at it.
        """
        target = os.path.join(self.outside, "CLEWs-PHL", "case", name)
        os.makedirs(os.path.join(target, "res", "BASE", "csv"))
        link = os.path.join(self.base, name)
        os.symlink(os.path.relpath(target, self.base), link)
        return target

    def test_symlinked_case_root_is_allowed(self):
        target = self._linked_case()
        self.assertEqual(self.Config.validate_path(self.base, "Philippines_v16"), target)

    def test_path_inside_symlinked_case_is_allowed(self):
        target = self._linked_case()
        result = self.Config.validate_path(
            self.base, os.path.join("Philippines_v16", "res", "BASE", "csv", "out.csv"))
        self.assertEqual(result, os.path.join(target, "res", "BASE", "csv", "out.csv"))

    def test_traversal_out_of_symlinked_case_is_blocked(self):
        self._linked_case()
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "Philippines_v16/../../../etc/passwd")

    def test_symlink_inside_symlinked_case_cannot_escape(self):
        # The allowance is for the DataStorage entry only. A second symlink
        # planted inside the linked case must not redirect the read onward.
        target = self._linked_case()
        os.symlink(self.outside, os.path.join(target, "escape"))
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "Philippines_v16/escape")

    def test_symlink_below_a_real_directory_cannot_escape(self):
        os.makedirs(os.path.join(self.base, "realcase"))
        os.symlink(self.outside, os.path.join(self.base, "realcase", "out"))
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, os.path.join("realcase", "out"))

    def test_dangling_symlink_is_blocked(self):
        os.symlink(os.path.join(self.outside, "gone"), os.path.join(self.base, "dangling"))
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "dangling")

    def test_symlink_to_a_plain_file_is_blocked(self):
        loose = os.path.join(self.outside, "loose.txt")
        with open(loose, "w", encoding="utf-8") as handle:
            handle.write("x")
        os.symlink(loose, os.path.join(self.base, "loosefile"))
        with self.assertRaises(PermissionError):
            self.Config.validate_path(self.base, "loosefile")


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


class DownloadRouteGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(API_DIR))
        os.environ.setdefault("MUIOGO_SECRET_KEY", "smoke-test-secret")
        cls.app_module = importlib.import_module("app")

    def setUp(self):
        self.client = self.app_module.app.test_client()

    def test_download_routes_require_active_session(self):
        endpoints = [
            ("/downloadDataFile", {"caserunname": "run1"}),
            ("/downloadFile", {"file": "result.csv"}),
            ("/downloadCSVFile", {"file": "result.csv", "caserunname": "run1"}),
            ("/downloadResultsFile", {"caserunname": "run1"}),
            ("/downloadCSV", {}),
        ]

        for path, query in endpoints:
            with self.subTest(path=path):
                response = self.client.get(path, query_string=query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.get_json(),
                    {
                        "message": "No active session. Please select a model first.",
                        "status_code": "error",
                    },
                )

    def test_download_routes_require_query_params(self):
        with self.client.session_transaction() as session_data:
            session_data["osycase"] = "demo"

        cases = [
            ("/downloadDataFile", {}, "Missing required parameter: caserunname."),
            ("/downloadFile", {}, "Missing required parameter: file."),
            ("/downloadCSVFile", {"caserunname": "run1"}, "Missing required parameter: file."),
            ("/downloadCSVFile", {"file": "result.csv"}, "Missing required parameter: caserunname."),
            ("/downloadResultsFile", {}, "Missing required parameter: caserunname."),
        ]

        for path, query, message in cases:
            with self.subTest(path=path, query=query):
                response = self.client.get(path, query_string=query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.get_json(),
                    {
                        "message": message,
                        "status_code": "error",
                    },
                )


if __name__ == "__main__":
    unittest.main()
