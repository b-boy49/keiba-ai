from pathlib import Path
import sys, tempfile, unittest
import pandas as pd
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.data import import_entity_csv, import_licensed_csv, load_authorized_training_csv
from keiba_ai.synthetic import make_synthetic_races
from keiba_ai.publish import publish_prediction_snapshot
from keiba_ai.rights import verify_provider_rights
from keiba_ai.registry import approve_candidate

ROOT = Path(__file__).resolve().parents[2]
WIKIDATA_RIGHTS = ROOT / "ai" / "rights" / "providers.json"

class RightsAndQualityTest(unittest.TestCase):
    def test_wikidata_is_limited_to_horse_metadata_and_provenance_detects_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            horses = root / "horses.csv"; horses.write_text("horse_id,horse_name\nQ1,Example Horse\n", encoding="utf-8")
            output = root / "approved-horses.csv"
            import_entity_csv(horses, output, record_type="horses", rights_manifest=WIKIDATA_RIGHTS, provider_id="wikidata-cc0")
            self.assertTrue(Path(f"{output}.provenance.json").exists())
            features = make_synthetic_races(root / "features.csv", races=12)
            with self.assertRaises(PermissionError):
                import_licensed_csv(features, root / "denied.csv", "Wikidata", True, rights_manifest=WIKIDATA_RIGHTS, provider_id="wikidata-cc0")

    def test_duplicate_entity_rows_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "horses.csv"; source.write_text("horse_id,horse_name\nQ1,A\nQ1,B\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                import_entity_csv(source, Path(directory) / "out.csv", record_type="horses", rights_manifest=WIKIDATA_RIGHTS, provider_id="wikidata-cc0")

    def test_real_training_file_requires_provenance_and_feature_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = make_synthetic_races(root / "source.csv", races=12)
            frame = pd.read_csv(source); frame["is_synthetic"] = False; frame.to_csv(root / "untracked.csv", index=False)
            with self.assertRaises(ValueError): load_authorized_training_csv(root / "untracked.csv")

    def test_publication_rejects_provider_without_training_and_public_rights(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); candidate = root / "candidate"; candidate.mkdir()
            metadata = {"version": "candidate-real", "contains_synthetic": False, "approval": "approved", "rights_verified": True, "dataset_provenance": {"provider_id": "wikidata-cc0"}}
            (candidate / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            registry = root / "active.json"; registry.write_text(json.dumps({"active_model": str(candidate), "approved_manually": True}), encoding="utf-8")
            predictions = root / "predictions.csv"; predictions.write_text("race_id,horse_id,horse_name,predicted_rank,reference_win_score,model_version\nr1,h1,Horse,1,0.1,candidate-real\n", encoding="utf-8")
            with self.assertRaises(PermissionError):
                publish_prediction_snapshot(registry, predictions, "r1", "Wikidata", True, root / "published", WIKIDATA_RIGHTS, "wikidata-cc0")

    def test_research_only_provider_can_train_but_never_become_public_model(self):
        provider = verify_provider_rights(WIKIDATA_RIGHTS, "kblueleaf-jp-racing-horse-research", "training_features", {"ingest", "internal_storage", "ml_training"})
        self.assertEqual(provider["id"], "kblueleaf-jp-racing-horse-research")
        with self.assertRaises(PermissionError):
            verify_provider_rights(WIKIDATA_RIGHTS, "kblueleaf-jp-racing-horse-research", "training_features", {"public_display"})
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate"; candidate.mkdir()
            metadata = {"contains_synthetic": False, "rights_verified": True, "dataset_provenance": {"publication_permitted": False}, "dataset_races": 743, "metrics": {"races": 158}, "calibration_status": "holdout_measured_reference_score"}
            (candidate / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaises(PermissionError): approve_candidate(candidate, Path(directory) / "active.json")

if __name__ == "__main__": unittest.main()
