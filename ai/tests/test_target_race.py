from pathlib import Path
import sys, tempfile, unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.target_race import TARGET_RACE, build_target_features

class TargetRaceTest(unittest.TestCase):
    def test_confirmed_entries_and_only_pre_race_history_build_features(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pd.DataFrame([{"race_id": TARGET_RACE["race_id"], "horse_id": "TEST-H", "horse_name": "Test Horse", "jockey_id": "TEST-J", "entry_status": "CONFIRMED"}]).to_csv(root / "entries.csv", index=False)
            pd.DataFrame([{"race_id": "PAST-1", "horse_id": "TEST-H", "jockey_id": "TEST-J", "race_date": "2026-10-01T00:00:00Z", "course_id": "tokyo", "surface": "DIRT", "distance_m": 2100, "finish_position": 2}]).to_csv(root / "past.csv", index=False)
            output = build_target_features(root / "entries.csv", root / "past.csv", root / "features.csv", "2026-11-06T00:00:00Z")
            frame = pd.read_csv(output); self.assertEqual(frame.iloc[0]["race_id"], TARGET_RACE["race_id"]); self.assertEqual(frame.iloc[0]["distance_experience"], 1); self.assertEqual(frame.iloc[0]["tokyo_starts"], 1); self.assertEqual(str(frame.iloc[0]["place_id"]).zfill(2), "05"); self.assertEqual(frame.iloc[0]["recent3_finish_avg"], 2)

    def test_unconfirmed_entries_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pd.DataFrame([{"race_id": TARGET_RACE["race_id"], "horse_id": "TEST-H", "horse_name": "Test Horse", "jockey_id": "TEST-J", "entry_status": "REGISTERED"}]).to_csv(root / "entries.csv", index=False)
            pd.DataFrame(columns=["horse_id", "jockey_id", "race_date", "course_id", "surface", "distance_m", "finish_position"]).to_csv(root / "past.csv", index=False)
            with self.assertRaises(ValueError): build_target_features(root / "entries.csv", root / "past.csv", root / "features.csv", "2026-11-06T00:00:00Z")

if __name__ == "__main__": unittest.main()
