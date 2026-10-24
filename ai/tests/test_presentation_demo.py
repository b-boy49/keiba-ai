from pathlib import Path
import sys, tempfile, unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.presentation_demo import EVALUATION, WITHHELD_NAME, _evaluation_summary, _load_verified_names, _outcome, select_demo_races


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

    def test_outcomes_keep_three_hit_definitions_separate(self):
        predicted = [
            {"horse_name": "A", "actual_finish": 4},
            {"horse_name": "B", "actual_finish": 1},
            {"horse_name": "C", "actual_finish": 8},
        ]
        actual = [{"horse_name": "B", "finish_position": 1}]
        self.assertEqual(_outcome(predicted, actual), {"top1_winner": False, "winner_in_top3": True, "top3_finish": True})

    def test_evaluation_summary_rejects_mismatched_metrics(self):
        metadata = {"test_metrics": {"model": {"winner_top1_accuracy": EVALUATION["top1_rate"] / 100, "winner_top3_recall": EVALUATION["top3_rate"] / 100, "races": EVALUATION["races"]}}}
        self.assertEqual(_evaluation_summary(metadata)["races"], 158)
        metadata["test_metrics"]["model"]["races"] = 157
        with self.assertRaises(ValueError):
            _evaluation_summary(metadata)

    def test_withheld_label_is_not_a_horse_name(self):
        self.assertIn("非表示", WITHHELD_NAME)


if __name__ == "__main__": unittest.main()
