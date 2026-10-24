from pathlib import Path
import sys, tempfile, unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.csv_schemas import validate_entity_frame
from keiba_ai.target_intake import history_coverage_report, validate_target_identities
from keiba_ai.target_race import TARGET_RACE


class TargetIntakeTest(unittest.TestCase):
    def _entries(self):
        return pd.DataFrame([{"race_id": TARGET_RACE["race_id"], "horse_id": "H1", "horse_name": "Horse One", "jockey_id": "J1", "jockey_name": "Jockey One", "entry_status": "CONFIRMED", "gate_no": 1, "horse_no": 1, "carried_weight_kg": 57.0, "published_at": "2026-11-06T00:00:00Z"}])

    def test_identity_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._entries().to_csv(root / "entries.csv", index=False)
            pd.DataFrame([{"horse_id": "H1", "horse_name": "Different"}]).to_csv(root / "horses.csv", index=False)
            pd.DataFrame([{"jockey_id": "J1", "jockey_name": "Jockey One"}]).to_csv(root / "jockeys.csv", index=False)
            with self.assertRaises(ValueError): validate_target_identities(root / "entries.csv", root / "horses.csv", root / "jockeys.csv")

    def test_invalid_gate_and_weight_are_rejected(self):
        entries = self._entries(); entries.loc[0, "gate_no"] = 9; entries.loc[0, "carried_weight_kg"] = 75
        with self.assertRaises(ValueError): validate_entity_frame(entries, "entries")

    def test_coverage_marks_no_recent_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._entries().to_csv(root / "entries.csv", index=False)
            pd.DataFrame([{"race_id": "OLD", "horse_id": "H1", "jockey_id": "J1", "race_date": "2024-12-01", "course_id": "tokyo", "finish_position": 1, "surface": "DIRT", "distance_m": 2100, "track_condition": "GOOD"}]).to_csv(root / "past.csv", index=False)
            report = pd.read_csv(history_coverage_report(root / "entries.csv", root / "past.csv", root / "report.csv", "2026-11-06T00:00:00Z"))
            self.assertEqual(report.iloc[0]["history_status"], "INSUFFICIENT")
            self.assertIn("no_result_since_2025_03_01", report.iloc[0]["missing_reason"])


if __name__ == "__main__": unittest.main()
