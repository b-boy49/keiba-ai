from pathlib import Path
import json
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.race_prediction import build_race_features, race_history_coverage_report


class ConfiguredRacePredictionTest(unittest.TestCase):
    def _spec(self, root: Path) -> Path:
        path = root / "race.json"
        path.write_text(json.dumps({"race_id": "niigata-20261024-08", "race_date": "2026-10-24", "course_id": "niigata", "place_id": "04", "race_no": 8, "race_name": "Race", "surface": "DIRT", "distance_m": 1800}), encoding="utf-8")
        return path

    def _entries(self) -> pd.DataFrame:
        return pd.DataFrame([{"race_id": "niigata-20261024-08", "horse_id": "H1", "horse_name": "Horse One", "jockey_id": "J1", "entry_status": "CONFIRMED", "gate_no": 1, "horse_no": 1, "carried_weight_kg": 57.0}])

    def test_empty_history_is_nan_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._entries().to_csv(root / "entries.csv", index=False)
            pd.DataFrame(columns=["horse_id", "jockey_id", "race_date", "course_id", "surface", "distance_m", "finish_position"]).to_csv(root / "past.csv", index=False)
            out = build_race_features(spec_path=self._spec(root), entries_path=root / "entries.csv", performances_path=root / "past.csv", output_path=root / "features.csv", feature_as_of="2026-10-23T00:00:00Z")
            row = pd.read_csv(out).iloc[0]
            self.assertTrue(pd.isna(row["recent_finish_avg"]))
            self.assertTrue(pd.isna(row["recent5_win_rate"]))

    def test_future_history_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._entries().to_csv(root / "entries.csv", index=False)
            pd.DataFrame([{"horse_id": "H1", "jockey_id": "J1", "race_date": "2026-10-25T00:00:00Z", "course_id": "niigata", "surface": "DIRT", "distance_m": 1800, "finish_position": 1}]).to_csv(root / "past.csv", index=False)
            with self.assertRaises(ValueError):
                build_race_features(spec_path=self._spec(root), entries_path=root / "entries.csv", performances_path=root / "past.csv", output_path=root / "features.csv", feature_as_of="2026-10-23T00:00:00Z")

    def test_scratched_runner_is_not_ranked_and_history_gap_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = pd.concat([self._entries(), pd.DataFrame([{
                "race_id": "niigata-20261024-08", "horse_id": "H2", "horse_name": "Horse Two",
                "jockey_id": "J2", "entry_status": "SCRATCHED", "gate_no": 2, "horse_no": 2,
                "carried_weight_kg": 57.0,
            }])], ignore_index=True)
            entries.to_csv(root / "entries.csv", index=False)
            pd.DataFrame(columns=["horse_id", "jockey_id", "race_date", "course_id", "surface", "distance_m", "finish_position"]).to_csv(root / "past.csv", index=False)
            spec = json.loads(self._spec(root).read_text(encoding="utf-8")); spec["expected_confirmed_runners"] = 1
            (root / "race.json").write_text(json.dumps(spec), encoding="utf-8")
            features = pd.read_csv(build_race_features(spec_path=root / "race.json", entries_path=root / "entries.csv", performances_path=root / "past.csv", output_path=root / "features.csv", feature_as_of="2026-10-23T00:00:00Z"))
            report = pd.read_csv(race_history_coverage_report(spec_path=root / "race.json", entries_path=root / "entries.csv", performances_path=root / "past.csv", output_path=root / "coverage.csv", feature_as_of="2026-10-23T00:00:00Z"))
            self.assertEqual(features["horse_id"].tolist(), ["H1"])
            self.assertEqual(report["horse_id"].tolist(), ["H1"])
            self.assertEqual(report.loc[0, "inference_eligibility"], "MODEL_CAN_HANDLE_HISTORY_GAP")


if __name__ == "__main__":
    unittest.main()
