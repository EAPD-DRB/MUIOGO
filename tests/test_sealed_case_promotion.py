from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.sealed_case_promotion import promote_case, seal_case, verify_seal


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SealedCasePromotionTest(unittest.TestCase):
    def make_candidate(self, root: Path, name: str = ".candidate") -> Path:
        case = root / name
        run = case / "res" / "BASE"
        run.mkdir(parents=True)
        (case / "documentation").mkdir()
        (case / "genData.json").write_text('{"osy-name": "Example"}\n', encoding="utf-8")
        qualification = case / "documentation" / "qualification.json"
        qualification.write_text('{"promotion_allowed": true}\n', encoding="utf-8")
        for filename in ("data.txt", "data_processed.txt", "lp.lp", "cbc.log", "results.txt"):
            (run / filename).write_text(filename + "\n", encoding="utf-8")
        (run / "generation_matrix_report.json").write_text(
            json.dumps({"status": "passed", "optimizer_runs": 0}) + "\n", encoding="utf-8"
        )
        (run / "optimization_record.json").write_text(
            json.dumps({
                "status": "Optimal - objective value 1",
                "optimizer_runs": 1,
                "scenario": "BASE",
                "objective": 1.0,
                "lp_sha256": digest(run / "lp.lp"),
                "results_sha256": digest(run / "results.txt"),
            }) + "\n",
            encoding="utf-8",
        )
        return case

    def test_seal_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_candidate(Path(temporary))
            seal_case(case, "Live", ["BASE"], Path("documentation/qualification.json"))
            verify_seal(case)
            (case / "genData.json").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "sealed candidate changed"):
                verify_seal(case)

    def test_promote_is_content_preserving_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = self.make_candidate(root)
            live = root / "Live"
            backup = root / "Live.prepromotion"
            live.mkdir()
            (live / "old.txt").write_text("old\n", encoding="utf-8")
            seal_case(candidate, "Live", ["BASE"], Path("documentation/qualification.json"))
            self.assertEqual(promote_case(candidate, live, backup, execute=False)["status"], "ready")
            self.assertEqual(promote_case(candidate, live, backup, execute=True)["status"], "promoted")
            self.assertTrue((backup / "old.txt").is_file())
            self.assertTrue((live / "documentation" / "SEALED_CANDIDATE.json").is_file())
            verify_seal(live)


if __name__ == "__main__":
    unittest.main()
