from pathlib import Path
import sys, tempfile, unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.presentation_demo import _load_verified_names, select_demo_races


class PresentationDemoTest(unittest.TestCase):
    def test_selection_is_earliest_dates_not_prediction_or_result_based(self):
        frame = pd.DataFrame({"race_id": ["late", "late", "early-b", "early-a", "middle"], "race_date": pd.to_datetime(["2020-03-01", "2020-03-01", "2020-01-01", "2020-01-01", "2020-02-01"], utc=True)})
        self.assertEqual(select_demo_races(frame, 3), ["early-a", "early-b", "middle"])

    def test_names_require_confirmed_jra_local_display_records(self):
        selected = pd.DataFrame({"race_id": ["R1"], "horse_id": ["H1"]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "names.csv"
            pd.DataFrame([{"race_id": "R1", "horse_id": "H1", "horse_name": "Verified Horse", "source_url": "https://www.jra.go.jp/example", "confirmed_at": "2026-10-24T00:00:00Z", "verification_status": "CONFIRMED", "display_scope": "LOCAL_PRESENTATION"}]).to_csv(path, index=False)
            self.assertEqual(_load_verified_names(path, selected), {("R1", "H1"): "Verified Horse"})


if __name__ == "__main__": unittest.main()
