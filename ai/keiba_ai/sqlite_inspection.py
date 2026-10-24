"""Read-only SQLite quality inspection for quarantined research datasets."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any


def _table_name(connection: sqlite3.Connection, expected: str) -> str:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    matches = [str(row[0]) for row in rows if str(row[0]).lower() == expected.lower()]
    if len(matches) != 1:
        raise ValueError(f"Required table not found exactly once: {expected}")
    return matches[0]


def _identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def inspect_racing_sqlite(path: str | Path) -> dict[str, Any]:
    """Return a compact report without mutating or copying the source database."""
    database = Path(path)
    if not database.is_file():
        raise FileNotFoundError(database)
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        race = _table_name(connection, "Race")
        horse = _table_name(connection, "Horse")
        def columns(table: str) -> list[str]:
            return [str(row[1]) for row in connection.execute(f"PRAGMA table_info({_identifier(table)})")]
        def count(table: str) -> int:
            return int(connection.execute(f"SELECT COUNT(*) FROM {_identifier(table)}").fetchone()[0])
        def nulls(table: str, column: str) -> int:
            return int(connection.execute(f"SELECT COUNT(*) FROM {_identifier(table)} WHERE {_identifier(column)} IS NULL OR TRIM(CAST({_identifier(column)} AS TEXT)) = ''").fetchone()[0])
        race_columns, horse_columns = columns(race), columns(horse)
        required_race, required_horse = {"rid", "date", "place_id", "course", "distance", "horses"}, {"hid", "name", "races"}
        if not required_race <= set(race_columns) or not required_horse <= set(horse_columns):
            raise ValueError("Database tables do not match the documented Race/Horse schema")
        duplicate_rid = int(connection.execute(f"SELECT COUNT(*) - COUNT(DISTINCT rid) FROM {_identifier(race)}").fetchone()[0])
        duplicate_hid = int(connection.execute(f"SELECT COUNT(*) - COUNT(DISTINCT hid) FROM {_identifier(horse)}").fetchone()[0])
        date_range = connection.execute(f"SELECT MIN(date), MAX(date) FROM {_identifier(race)} WHERE date IS NOT NULL AND TRIM(date) != ''").fetchone()
        distance_invalid = int(connection.execute(f"SELECT COUNT(*) FROM {_identifier(race)} WHERE distance IS NULL OR CAST(distance AS INTEGER) <= 0 OR CAST(distance AS INTEGER) > 10000").fetchone()[0])
        json_invalid = 0
        horse_list_shape: dict[str, Any] | None = None
        for row in connection.execute(f"SELECT horses FROM {_identifier(race)} WHERE horses IS NOT NULL"):
            try:
                parsed = json.loads(row[0])
                if horse_list_shape is None:
                    entries = parsed[0] if isinstance(parsed, list) and parsed and isinstance(parsed[0], list) else parsed
                    first = entries[0] if isinstance(entries, list) and entries else None
                    horse_list_shape = {"outer_type": type(parsed).__name__, "outer_length": len(parsed) if isinstance(parsed, list) else None, "entry_collection_type": type(entries).__name__, "entry_count": len(entries) if isinstance(entries, list) else None, "entry_type": type(first).__name__ if first is not None else None, "entry_field_count": len(first) if isinstance(first, list) else None}
            except (TypeError, json.JSONDecodeError):
                json_invalid += 1
        return {
            "database": str(database),
            "mode": "read-only quarantine inspection",
            "tables": {race: {"records": count(race), "columns": race_columns, "nulls": {column: nulls(race, column) for column in race_columns}, "duplicate_rid": duplicate_rid, "date_min": date_range[0], "date_max": date_range[1], "invalid_distance": distance_invalid, "invalid_horses_json": json_invalid, "horses_json_shape": horse_list_shape, "place_id_counts": {str(row[0]): int(row[1]) for row in connection.execute(f"SELECT place_id, COUNT(*) FROM {_identifier(race)} GROUP BY place_id ORDER BY place_id")}}, horse: {"records": count(horse), "columns": horse_columns, "nulls": {column: nulls(horse, column) for column in horse_columns}, "duplicate_hid": duplicate_hid}},
            "suitable_for_training": False,
            "reason": "Quarantine inspection only; legal/provider review and a separate approval are required before conversion or model training.",
        }
    finally:
        connection.close()


def write_inspection_report(path: str | Path, output: str | Path) -> Path:
    report = inspect_racing_sqlite(path)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
