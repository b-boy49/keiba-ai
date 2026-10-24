from pathlib import Path
import sys, tempfile, unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keiba_ai.all_dirt_research import _splits

class AllDirtResearchTest(unittest.TestCase):
    def test_all_dirt_training_is_cut_off_before_target_validation(self):
        rows = []
        for day in range(15):
            date = pd.Timestamp("2020-01-01", tz="UTC") + pd.Timedelta(days=day)
            for race, place, distance in [("target", "05", 2100), ("extra", "01", 1800)]:
                for horse in range(2): rows.append({"race_id": f"{race}-{day}", "race_date": date, "surface": "DIRT", "distance_m": distance, "place_id": place, "horse_id": f"{race}-{day}-{horse}", "finish_position": horse + 1})
        train, validation, test, target = _splits(pd.DataFrame(rows))
        self.assertGreater(train["race_id"].nunique(), target.loc[target["race_date"] <= train["race_date"].max(), "race_id"].nunique())
        self.assertLess(train["race_date"].max(), validation["race_date"].min())
        self.assertLess(validation["race_date"].max(), test["race_date"].min())

if __name__ == "__main__": unittest.main()
