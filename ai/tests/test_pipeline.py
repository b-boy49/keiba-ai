from pathlib import Path
import sys, tempfile, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.data import read_race_csv
from keiba_ai.synthetic import make_synthetic_races
from keiba_ai.training import load_bundle, predict, train_candidate
from keiba_ai.registry import approve_candidate
from keiba_ai.publish import publish_prediction_snapshot

class PipelineTest(unittest.TestCase):
    def test_synthetic_candidate_is_ranked_and_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); csv = make_synthetic_races(root / "synthetic.csv", races=30); candidate, metrics = train_candidate(read_race_csv(csv), root / "artifacts"); output = predict(load_bundle(candidate), read_race_csv(csv))
            self.assertEqual(len(output), 30 * 12); self.assertEqual(output.groupby("race_id")["predicted_rank"].min().eq(1).all(), True); self.assertGreaterEqual(metrics.brier, 0)
            with self.assertRaises(ValueError): approve_candidate(candidate, root / "active.json")
            with self.assertRaises(ValueError): publish_prediction_snapshot(root / "active.json", root / "predictions.csv", "race-1", "synthetic", True, root / "published")

if __name__ == "__main__": unittest.main()
