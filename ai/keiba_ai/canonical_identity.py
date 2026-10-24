"""Fail-closed canonical-ID resolution against the quarantined SQLite master.

This module deliberately performs exact, normalized name matching only.  It
never invents an ID, never applies fuzzy matching, and never writes to the
research database.  The resulting CSV is an internal review artifact; an
operator must still approve and import it through the rights-checked intake.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pandas as pd


def _normalise(value: object) -> str:
    return "".join(str(value).strip().split())


def _readonly_connection(path: str | Path) -> sqlite3.Connection:
    database = Path(path)
    if not database.is_file():
        raise FileNotFoundError(database)
    return sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)


def _horse_master(path: str | Path) -> pd.DataFrame:
    connection = _readonly_connection(path)
    try:
        columns = {str(row[1]) for row in connection.execute('PRAGMA table_info("Horse")')}
        if not {"hid", "name"} <= columns:
            raise ValueError("SQLite Horse table does not contain hid/name canonical fields")
        rows = connection.execute('SELECT hid, name FROM "Horse" WHERE hid IS NOT NULL AND name IS NOT NULL').fetchall()
    finally:
        connection.close()
    master = pd.DataFrame(rows, columns=["canonical_horse_id", "master_horse_name"])
    master["canonical_horse_id"] = master["canonical_horse_id"].astype(str).str.strip()
    master["master_horse_name"] = master["master_horse_name"].astype(str).str.strip()
    master["_key"] = master["master_horse_name"].map(_normalise)
    return master.loc[master["_key"].ne("")].copy()


def resolve_race_card_identities(*, entries_path: str | Path, sqlite_path: str | Path, output_path: str | Path) -> Path:
    """Write an exact-match review CSV for a supplied, authorised race card.

    Horse names with zero or multiple SQLite candidates remain unresolved.  The
    inspected schema has no jockey-name master, so the jockey result is always
    ``JOCKEY_MASTER_UNAVAILABLE`` until a separately approved mapping is
    supplied.  This makes a name-only jockey join impossible by construction.
    """
    entries = pd.read_csv(entries_path, dtype=str).fillna("")
    required = {"race_id", "horse_name", "jockey_name", "entry_status"}
    if missing := required - set(entries.columns):
        raise ValueError(f"Race-card CSV missing columns: {', '.join(sorted(missing))}")
    if entries.empty:
        raise ValueError("Race-card CSV has no entries")
    master = _horse_master(sqlite_path)
    grouped = master.groupby("_key", sort=False)
    rows: list[dict[str, object]] = []
    for entry in entries.itertuples(index=False):
        key = _normalise(entry.horse_name)
        candidates = grouped.get_group(key) if key in grouped.groups else master.iloc[0:0]
        status = "MATCHED_EXACT" if len(candidates) == 1 else ("NOT_FOUND" if candidates.empty else "AMBIGUOUS_NAME")
        canonical = str(candidates.iloc[0]["canonical_horse_id"]) if status == "MATCHED_EXACT" else ""
        supplied = str(getattr(entry, "horse_id", "")).strip()
        if supplied and canonical and supplied != canonical:
            status, canonical = "SUPPLIED_ID_CONFLICT", ""
        rows.append({
            "race_id": str(entry.race_id),
            "horse_name": str(entry.horse_name),
            "supplied_horse_id": supplied,
            "canonical_horse_id": canonical,
            "horse_resolution": status,
            "jockey_name": str(entry.jockey_name),
            "supplied_jockey_id": str(getattr(entry, "jockey_id", "")).strip(),
            "canonical_jockey_id": "",
            "jockey_resolution": "JOCKEY_MASTER_UNAVAILABLE",
            "entry_status": str(entry.entry_status),
            "review_required": "YES" if status != "MATCHED_EXACT" else "YES",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolution_method": "exact_normalized_name_only_readonly_sqlite",
        })
    target = Path(output_path)
    quarantine = Path("ai/quarantine").resolve()
    if quarantine not in target.resolve().parents:
        raise PermissionError("Identity-review output must remain under ai/quarantine")
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(target, index=False, encoding="utf-8")
    return target
