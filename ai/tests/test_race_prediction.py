from pathlib import Path
import json
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.race_prediction import build_race_features


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


if __name__ == "__main__":
    unittest.main()
