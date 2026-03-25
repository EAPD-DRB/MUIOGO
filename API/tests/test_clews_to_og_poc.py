import sys
import tempfile
import unittest
from pathlib import Path


REPO_API = Path(__file__).resolve().parents[1]
if str(REPO_API) not in sys.path:
    sys.path.insert(0, str(REPO_API))

from Integration.clews_to_og_poc import load_clews_result_csv, poc_pivot_clews_data


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


if __name__ == "__main__":
    unittest.main()
