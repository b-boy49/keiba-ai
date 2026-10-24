from pathlib import Path
import sys, tempfile, unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.wikidata import WikidataHorseClient, import_wikidata_horses, map_horse_entity

ROOT = Path(__file__).resolve().parents[2]
RIGHTS = ROOT / "ai" / "rights" / "providers.json"

ENTITY = {"id": "Q42", "labels": {"ja": {"value": "テストホース"}}, "claims": {
    "P569": [{"mainsnak": {"datavalue": {"value": {"time": "+2020-01-02T00:00:00Z"}}}}],
    "P22": [{"mainsnak": {"datavalue": {"value": {"id": "Q1"}}}}],
    "P25": [{"mainsnak": {"datavalue": {"value": {"id": "Q2"}}}}],
    "P999": [{"mainsnak": {"datatype": "external-id", "datavalue": {"value": "external-42"}}}],
}}

class WikidataImportTest(unittest.TestCase):
    def test_mapping_is_limited_to_metadata(self):
        row = map_horse_entity(ENTITY, "2026-10-23T00:00:00+00:00")
        self.assertEqual(row["horse_name"], "テストホース")
        self.assertEqual(row["sire_wikidata_id"], "Q1")
        self.assertNotIn("odds", row)

    def test_cached_or_mocked_entity_writes_rights_tracked_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); calls = []
            def fake_request(url, headers, timeout):
                calls.append((url, headers)); return {"entities": {"Q42": ENTITY}}
            client = WikidataHorseClient(root / "cache", "KEIBA-AI/0.9 (contact: admin@example.invalid)", request_json=fake_request, sleep=lambda _: None)
            output = import_wikidata_horses(["Q42"], root / "horses.csv", cache_dir=root / "cache", user_agent="KEIBA-AI/0.9 (contact: admin@example.invalid)", rights_manifest=RIGHTS, client=client)
            self.assertTrue(output.exists())
            self.assertTrue(Path(f"{output}.provenance.json").exists())
            self.assertEqual(len(calls), 1)
            self.assertTrue(client.get_entity("Q42")[1])
            self.assertEqual(len(calls), 1)

    def test_generic_user_agent_and_unknown_rights_are_rejected(self):
        with self.assertRaises(ValueError):
            WikidataHorseClient("cache", "Python-urllib/3")
        with self.assertRaises(ValueError):
            WikidataHorseClient("cache", "KEIBA-AI/0.9")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((PermissionError, ValueError)):
                import_wikidata_horses(["Q42"], Path(directory) / "out.csv", cache_dir=Path(directory) / "cache", user_agent="KEIBA-AI/0.9 (contact: admin@example.invalid)", rights_manifest=RIGHTS, provider_id="unknown")

if __name__ == "__main__": unittest.main()
