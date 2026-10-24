"""Chronological converter for the quarantined KBlueLeaf research database.

This converter is not a publication path. It uses only past dates to create
features for the historical Tokyo dirt 2100m evaluation cohort.
"""
from __future__ import annotations

from collections import defaultdict, deque
import csv
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd

TOKYO_PLACE_ID = "05"
TRACK_CONDITIONS = {0: "GOOD", 1: "YIELDING", 2: "HEAVY", 3: "BAD"}

ALL_DIRT_COLUMNS = [
    "race_id", "race_date", "feature_as_of", "horse_id", "horse_name", "jockey_id",
    "surface", "distance_m", "track_condition", "place_id", "gate_number", "horse_number",
    "carried_weight_kg", "field_size", "recent_finish_avg", "recent3_finish_avg",
    "distance_experience", "jockey_win_rate", "jockey_top3_rate", "days_since_last_run",
    "dirt_2100_finish_avg", "tokyo_starts", "tokyo_finish_avg", "current_course_starts",
    "current_course_finish_avg", "recent5_win_rate", "recent5_top3_rate", "jockey_horse_starts",
    "jockey_horse_finish_avg", "finish_position",
]


def _entries(raw: str | None) -> list[list[Any]]:
    if not raw:
        return []
    parsed = json.loads(raw)
    return [item for item in parsed if isinstance(item, list) and len(item) >= 11] if isinstance(parsed, list) else []


def _mean(values: list[float] | deque[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _entry_integer(entry: list[Any], index: int) -> int:
    try:
        return int(entry[index])
    except (IndexError, TypeError, ValueError):
        return 0


def _entry_float(entry: list[Any], index: int) -> float:
    try:
        return float(entry[index])
    except (IndexError, TypeError, ValueError):
        return 0.0


def convert_kblueleaf_all_dirt(source: str | Path, output: str | Path, *, min_distance: int = 0, max_distance: int = 9999) -> tuple[Path, dict[str, int]]:
    """Create a streamed, research-only all-dirt training set.

    Race results update history only after every race on the same calendar date
    has been converted.  The raw odds and final time fields in the source are
    deliberately not emitted, since they are not consistently available at the
    intended pre-race prediction point.
    """
    database, target = Path(source), Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        names = {str(row["hid"]): str(row["name"]) for row in connection.execute("SELECT hid, name FROM horse WHERE name IS NOT NULL AND TRIM(name) != ''")}
        histories: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "finishes": deque(maxlen=5), "distances": defaultdict(int), "dirt2100": [0.0, 0],
            "courses": defaultdict(lambda: [0.0, 0]), "last": None,
        })
        jockeys: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # wins, top3, starts
        pairs: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
        updates: list[tuple[datetime, str, str, int, int, str, int]] = []
        current_day: str | None = None
        races = entries = skipped = 0

        def update_day() -> None:
            for date, horse, jockey, finish, distance, place, surface in updates:
                history = histories[horse]
                history["finishes"].append(float(finish))
                history["distances"][distance] += 1
                history["last"] = date
                history["courses"][place][0] += float(finish)
                history["courses"][place][1] += 1
                if surface == 0 and distance == 2100:
                    history["dirt2100"][0] += float(finish)
                    history["dirt2100"][1] += 1
                jockeys[jockey][0] += int(finish == 1)
                jockeys[jockey][1] += int(finish <= 3)
                jockeys[jockey][2] += 1
                pairs[(horse, jockey)][0] += float(finish)
                pairs[(horse, jockey)][1] += 1
            updates.clear()

        with target.open("w", newline="", encoding="utf-8") as destination:
            writer = csv.DictWriter(destination, fieldnames=ALL_DIRT_COLUMNS)
            writer.writeheader()
            query = "SELECT rid, place_id, date, course, course_sit, distance, horses FROM race ORDER BY date, rid"
            for race in connection.execute(query):
                day = str(race["date"])
                if current_day is not None and day != current_day:
                    update_day()
                current_day = day
                try:
                    date = datetime.strptime(day, "%Y/%m/%d")
                    surface, distance, condition = int(race["course"]), int(race["distance"]), int(race["course_sit"])
                except (TypeError, ValueError):
                    continue
                place = str(race["place_id"]).zfill(2)
                race_entries = _entries(race["horses"])
                field_size = len(race_entries)
                is_dirt = surface == 0
                selected = is_dirt and min_distance <= distance <= max_distance
                if selected:
                    races += 1
                for entry in race_entries:
                    horse, jockey, finish = str(entry[0]), str(entry[10]), _entry_integer(entry, 1)
                    if finish <= 0 or horse not in names or not jockey:
                        skipped += 1
                        continue
                    if selected:
                        history, jockey_history, pair = histories[horse], jockeys[jockey], pairs[(horse, jockey)]
                        recent = list(history["finishes"])
                        course_history = history["courses"][place]
                        dirt2100 = history["dirt2100"]
                        last = history["last"]
                        writer.writerow({
                            "race_id": str(race["rid"]), "race_date": date.strftime("%Y-%m-%dT00:00:00Z"), "feature_as_of": date.strftime("%Y-%m-%dT00:00:00Z"),
                            "horse_id": horse, "horse_name": names[horse], "jockey_id": jockey, "surface": "DIRT", "distance_m": distance,
                            "track_condition": TRACK_CONDITIONS.get(condition, "UNKNOWN"), "place_id": place,
                            "gate_number": _entry_integer(entry, 2), "horse_number": _entry_integer(entry, 3), "carried_weight_kg": _entry_float(entry, 4), "field_size": field_size,
                            "recent_finish_avg": _mean(recent), "recent3_finish_avg": _mean(recent[-3:]), "distance_experience": history["distances"][distance],
                            "jockey_win_rate": float(jockey_history[0] / jockey_history[2]) if jockey_history[2] else 0.0,
                            "jockey_top3_rate": float(jockey_history[1] / jockey_history[2]) if jockey_history[2] else 0.0,
                            "days_since_last_run": (date - last).days if last else 3650,
                            "dirt_2100_finish_avg": float(dirt2100[0] / dirt2100[1]) if dirt2100[1] else 0.0,
                            "tokyo_starts": int(history["courses"][TOKYO_PLACE_ID][1]), "tokyo_finish_avg": float(history["courses"][TOKYO_PLACE_ID][0] / history["courses"][TOKYO_PLACE_ID][1]) if history["courses"][TOKYO_PLACE_ID][1] else 0.0,
                            "current_course_starts": int(course_history[1]), "current_course_finish_avg": float(course_history[0] / course_history[1]) if course_history[1] else 0.0,
                            "recent5_win_rate": float(sum(value == 1 for value in recent) / len(recent)) if recent else 0.0,
                            "recent5_top3_rate": float(sum(value <= 3 for value in recent) / len(recent)) if recent else 0.0,
                            "jockey_horse_starts": int(pair[1]), "jockey_horse_finish_avg": float(pair[0] / pair[1]) if pair[1] else 0.0,
                            "finish_position": finish,
                        })
                        entries += 1
                    updates.append((date, horse, jockey, finish, distance, place, surface))
            update_day()
    finally:
        connection.close()
    if not entries:
        raise ValueError("No dirt entries found; review source schema/track mapping")
    return target, {"races": races, "entries": entries, "skipped_entries": skipped, "min_distance": min_distance, "max_distance": max_distance}


def convert_kblueleaf_tokyo_dirt_2100(source: str | Path, output: str | Path) -> tuple[Path, dict[str, int]]:
    """Build target-like feature rows without same-day or future result leakage."""
    database = Path(source)
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        names = {str(row["hid"]): str(row["name"]) for row in connection.execute("SELECT hid, name FROM horse WHERE name IS NOT NULL AND TRIM(name) != ''")}
        histories: dict[str, dict[str, Any]] = defaultdict(lambda: {"finishes": deque(maxlen=5), "distances": defaultdict(int), "dirt2100": [], "tokyo": [], "last": None})
        jockeys: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        pairs: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
        rows: list[dict[str, Any]] = []; updates: list[tuple[datetime, str, str, int, int, str, int]] = []
        skipped = 0; current_day: str | None = None

        def update_day() -> None:
            for date, horse, jockey, finish, distance, place, surface in updates:
                history = histories[horse]; history["finishes"].append(float(finish)); history["distances"][distance] += 1; history["last"] = date
                if surface == 0 and distance == 2100: history["dirt2100"].append(float(finish))
                if place == TOKYO_PLACE_ID: history["tokyo"].append(float(finish))
                jockeys[jockey][0] += int(finish == 1); jockeys[jockey][1] += 1
                pairs[(horse, jockey)][0] += float(finish); pairs[(horse, jockey)][1] += 1
            updates.clear()

        query = "SELECT rid, place_id, date, course, course_sit, distance, horses FROM race ORDER BY date, rid"
        for race in connection.execute(query):
            day = str(race["date"])
            if current_day is not None and day != current_day: update_day()
            current_day = day
            try:
                date = datetime.strptime(day, "%Y/%m/%d"); surface = int(race["course"]); distance = int(race["distance"]); condition = int(race["course_sit"])
            except (TypeError, ValueError):
                continue
            place = str(race["place_id"]).zfill(2); target = place == TOKYO_PLACE_ID and surface == 0 and distance == 2100
            for entry in _entries(race["horses"]):
                horse, jockey = str(entry[0]), str(entry[10])
                try: finish = int(entry[1])
                except (TypeError, ValueError): finish = 0
                if finish <= 0 or horse not in names or not jockey:
                    skipped += 1; continue
                if target:
                    history, jockey_history, pair = histories[horse], jockeys[jockey], pairs[(horse, jockey)]
                    last = history["last"]
                    rows.append({"race_id": str(race["rid"]), "race_date": date.strftime("%Y-%m-%dT00:00:00Z"), "feature_as_of": date.strftime("%Y-%m-%dT00:00:00Z"), "horse_id": horse, "horse_name": names[horse], "jockey_id": jockey, "surface": "DIRT", "distance_m": 2100, "track_condition": TRACK_CONDITIONS.get(condition, "UNKNOWN"), "recent_finish_avg": _mean(history["finishes"]), "distance_experience": history["distances"][2100], "jockey_win_rate": float(jockey_history[0] / jockey_history[1]) if jockey_history[1] else 0.0, "days_since_last_run": (date - last).days if last else 3650, "dirt_2100_finish_avg": _mean(history["dirt2100"]), "tokyo_starts": len(history["tokyo"]), "tokyo_finish_avg": _mean(history["tokyo"]), "jockey_horse_starts": int(pair[1]), "jockey_horse_finish_avg": float(pair[0] / pair[1]) if pair[1] else 0.0, "finish_position": finish})
                updates.append((date, horse, jockey, finish, distance, place, surface))
        update_day()
    finally:
        connection.close()
    if not rows: raise ValueError("No Tokyo dirt 2100m rows found; review source schema/track mapping")
    frame = pd.DataFrame(rows).sort_values(["race_date", "race_id", "horse_id"])
    target = Path(output); target.parent.mkdir(parents=True, exist_ok=True); frame.to_csv(target, index=False)
    return target, {"races": int(frame["race_id"].nunique()), "entries": len(frame), "skipped_entries": skipped}
