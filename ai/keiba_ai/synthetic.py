from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

def make_synthetic_races(output_path: str | Path, races: int = 90, horses_per_race: int = 12, seed: int = 7) -> Path:
    """Create non-real rows solely for pipeline tests; never use these as racing data."""
    rng = np.random.default_rng(seed); rows = []; start = date(2023, 1, 7)
    for index in range(races):
        race_date = start + timedelta(days=index * 7); distance = int(rng.choice([1400, 1600, 1800, 2000, 2100])); surface = str(rng.choice(["TURF", "DIRT"])); condition = str(rng.choice(["GOOD", "YIELDING", "SOFT"], p=[.6, .25, .15]))
        latent = rng.normal(0, 1, horses_per_race)
        noise = rng.normal(0, .7, horses_per_race); ranking = np.argsort(-(latent + noise))
        finish = np.empty(horses_per_race, dtype=int); finish[ranking] = np.arange(1, horses_per_race + 1)
        for runner in range(horses_per_race):
            rows.append({"race_id": f"SYN-{index:04d}", "race_date": race_date.isoformat(), "horse_id": f"SYN-H-{index:04d}-{runner:02d}", "horse_name": f"Synthetic Horse {index:04d}-{runner:02d}", "jockey_id": f"SYN-J-{runner % 20:02d}", "surface": surface, "distance_m": distance, "track_condition": condition, "recent_finish_avg": round(float(np.clip(6.5 - latent[runner] * 1.2 + rng.normal(0, .6), 1, 12)), 3), "distance_experience": int(rng.integers(0, 12)), "jockey_win_rate": round(float(np.clip(.08 + latent[runner] * .025 + rng.normal(0, .018), .01, .3)), 4), "days_since_last_run": int(rng.integers(14, 160)), "dirt_2100_finish_avg": round(float(rng.uniform(2, 10)), 3), "tokyo_starts": int(rng.integers(0, 10)), "tokyo_finish_avg": round(float(rng.uniform(2, 10)), 3), "jockey_horse_starts": int(rng.integers(0, 7)), "jockey_horse_finish_avg": round(float(rng.uniform(2, 10)), 3), "finish_position": int(finish[runner]), "data_source": "synthetic-test-data", "is_synthetic": True})
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_csv(target, index=False); return target
