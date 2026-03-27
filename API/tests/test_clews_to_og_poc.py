import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_API = Path(__file__).resolve().parents[1]
if str(REPO_API) not in sys.path:
    sys.path.insert(0, str(REPO_API))

from Integration.clews_to_og_poc import (
    build_clews_input_manifest,
    load_clews_result_csv,
    poc_pivot_clews_data,
    write_coupled_integration_outputs,
)


class ClewsToOgPocTests(unittest.TestCase):
    def test_load_clews_result_csv_validates_expected_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "CapitalInvestment.csv"
            csv_path.write_text(
                "r,t,y,CapitalInvestment\n"
                "RE1,SOLAR,2025,10.5\n"
                "RE1,WIND,2025,12.0\n",
                encoding="utf-8",
            )

            df = load_clews_result_csv(str(csv_path))

            self.assertEqual(
                list(df.columns), ["r", "t", "y", "CapitalInvestment"]
            )
            self.assertEqual(df["CapitalInvestment"].tolist(), [10.5, 12.0])

    def test_poc_pivot_clews_data_builds_year_by_technology_matrix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "CapitalInvestment.csv"
            csv_path.write_text(
                "r,t,y,CapitalInvestment\n"
                "RE1,SOLAR,2025,10\n"
                "RE1,SOLAR,2025,2\n"
                "RE1,WIND,2025,5\n"
                "RE1,SOLAR,2026,3\n",
                encoding="utf-8",
            )

            matrix = poc_pivot_clews_data(str(csv_path))

            self.assertEqual(matrix.index.tolist(), [2025, 2026])
            self.assertEqual(matrix.columns.tolist(), ["SOLAR", "WIND"])
            self.assertEqual(matrix.loc[2025, "SOLAR"], 12.0)
            self.assertEqual(matrix.loc[2025, "WIND"], 5.0)
            self.assertEqual(matrix.loc[2026, "SOLAR"], 3.0)
            self.assertEqual(matrix.loc[2026, "WIND"], 0.0)

    def test_poc_pivot_clews_data_rejects_missing_dimensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "CapitalInvestment.csv"
            csv_path.write_text(
                "r,y,CapitalInvestment\n"
                "RE1,2025,10\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Missing expected columns"):
                poc_pivot_clews_data(str(csv_path))

    def test_build_clews_input_manifest_describes_validated_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_root = Path(tmpdir) / "Kenya" / "res" / "run_001"
            csv_dir = run_root / "csv"
            csv_dir.mkdir(parents=True)
            csv_path = csv_dir / "CapitalInvestment.csv"
            csv_path.write_text(
                "r,t,y,CapitalInvestment\n"
                "RE1,SOLAR,2025,10\n"
                "RE1,WIND,2025,5\n"
                "RE1,SOLAR,2026,3\n",
                encoding="utf-8",
            )

            manifest = build_clews_input_manifest(str(csv_path), run_root=run_root)

            self.assertEqual(manifest["case_name"], "Kenya")
            self.assertEqual(manifest["run_name"], "run_001")
            self.assertEqual(manifest["schema_version"], "0.1")
            self.assertEqual(len(manifest["inputs"]), 1)
            record = manifest["inputs"][0]
            self.assertEqual(record["source_csv"], "csv/CapitalInvestment.csv")
            self.assertEqual(record["dimensions"], ["r", "t", "y"])
            self.assertEqual(record["row_count"], 3)
            self.assertEqual(record["years"], [2025, 2026])
            self.assertEqual(record["dimension_members"]["t"], ["SOLAR", "WIND"])

    def test_write_coupled_integration_outputs_generates_manifest_and_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_root = Path(tmpdir) / "Kenya" / "res" / "run_001"
            csv_dir = run_root / "csv"
            csv_dir.mkdir(parents=True)
            csv_path = csv_dir / "CapitalInvestment.csv"
            csv_path.write_text(
                "r,t,y,CapitalInvestment\n"
                "RE1,SOLAR,2025,10\n"
                "RE1,SOLAR,2025,2\n"
                "RE1,WIND,2025,5\n"
                "RE1,SOLAR,2026,3\n",
                encoding="utf-8",
            )

            written = write_coupled_integration_outputs(str(csv_path), run_root=run_root)

            manifest_path = written["manifest_path"]
            summary_path = written["summary_path"]
            self.assertTrue(manifest_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertEqual(manifest_path.parent, run_root / "integration")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(
                summary["generated_files"]["clews_input_manifest"],
                "integration/clews_input_manifest.json",
            )
            self.assertEqual(summary["workflow"], "coupled")
            self.assertEqual(summary["status"], "ready_for_ogcore_adapter")
            self.assertEqual(summary["source_results_dir"], "csv")
            self.assertEqual(summary["variables"], ["CapitalInvestment"])
            self.assertEqual(
                summary["transforms"][0]["output_kind"], "year_by_technology_matrix"
            )
            self.assertEqual(summary["transforms"][0]["years"], [2025, 2026])
            self.assertEqual(summary["transforms"][0]["technologies"], ["SOLAR", "WIND"])
            self.assertEqual(manifest["inputs"][0]["source_csv"], "csv/CapitalInvestment.csv")


if __name__ == "__main__":
    unittest.main()
