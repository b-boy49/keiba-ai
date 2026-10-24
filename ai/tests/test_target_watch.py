from pathlib import Path
import sys, tempfile, unittest
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.target_watch import _card_state, _inputs, run_target_watch


class TargetWatchTest(unittest.TestCase):
    def test_missing_files_are_detected_without_prediction(self):
        with tempfile.TemporaryDirectory() as directory:
            files, missing = _inputs(Path(directory))
            self.assertIsNone(files)
            self.assertEqual(set(missing), {"entries.csv", "post-2025-results.csv", "horses.csv", "jockeys.csv"})

    def test_card_distinguishes_entries_and_gate_confirmation(self):
        base = {"race_id": "tokyo-20261107-09", "entry_status": "CONFIRMED", "gate_no": 1, "horse_no": 1}
        self.assertEqual(_card_state(pd.DataFrame([base])), "CONFIRMED")
        self.assertEqual(_card_state(pd.DataFrame([{**base, "entry_status": "REGISTERED"}])), "ENTRY_WAITING")
        self.assertEqual(_card_state(pd.DataFrame([{**base, "gate_no": 0}])), "GATE_WAITING")

    def test_unchanged_input_is_not_predicted_twice_and_changed_input_retries(self):
        with tempfile.TemporaryDirectory(dir="ai/quarantine") as directory:
            root = Path(directory); intake, output = root / "intake", root / "predictions"; intake.mkdir()
            pd.DataFrame([{"race_id": "tokyo-20261107-09", "entry_status": "CONFIRMED", "gate_no": 1, "horse_no": 1}]).to_csv(intake / "entries.csv", index=False)
            for name in ("post-2025-results.csv", "horses.csv", "jockeys.csv"):
                (intake / name).write_text("value\n1\n", encoding="utf-8")
            calls = []
            def coverage(*args):
                pd.DataFrame([{"history_status": "SUFFICIENT"}]).to_csv(args[2], index=False)
            def prediction(**kwargs):
                calls.append(kwargs); Path(kwargs["output_path"]).parent.mkdir(parents=True, exist_ok=True); Path(kwargs["output_path"]).write_text("ok", encoding="utf-8")
            with patch("keiba_ai.target_watch.verify_dataset_purpose"), patch("keiba_ai.target_watch.history_coverage_report", side_effect=coverage), patch("keiba_ai.target_watch.predict_target_research", side_effect=prediction):
                common = {"intake_dir": intake, "output_dir": output, "model_dir": "ai/quarantine/artifacts/x", "registry_path": "ai/quarantine/research-active.json", "feature_as_of": "2026-11-06T00:00:00Z"}
                self.assertEqual(run_target_watch(**common)["state"], "PREDICTION_COMPLETE")
                self.assertEqual(run_target_watch(**common)["state"], "PREDICTION_CURRENT")
                (intake / "entries.csv").write_text("race_id,entry_status,gate_no,horse_no\ntokyo-20261107-09,CONFIRMED,1,2\n", encoding="utf-8")
                self.assertEqual(run_target_watch(**common)["state"], "PREDICTION_COMPLETE")
            self.assertEqual(len(calls), 2)


if __name__ == "__main__": unittest.main()
