"""Human-operated, cache-first Wikidata horse metadata importer.

This module intentionally knows nothing about race cards or results.  Wikidata
metadata may support entity matching, but it never authorizes JRA data use.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .rights import verify_provider_rights, write_provenance

ACTION_API = "https://www.wikidata.org/w/api.php"
QID = re.compile(r"^Q[1-9][0-9]*$")


class WikidataRequestError(RuntimeError):
    """A request could not be completed safely after the bounded retries."""


def _claim_value(entity: dict[str, Any], property_id: str) -> str:
    claims = entity.get("claims", {}).get(property_id, [])
    for claim in claims:
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            return str(value["id"])
        if isinstance(value, dict) and value.get("time"):
            return str(value["time"])
        if value is not None:
            return str(value)
    return ""


def _label(entity: dict[str, Any]) -> str:
    labels = entity.get("labels", {})
    return str(labels.get("ja", {}).get("value") or labels.get("en", {}).get("value") or "")


def map_horse_entity(entity: dict[str, Any], retrieved_at: str) -> dict[str, str]:
    """Map only stable, explicitly documented Wikidata fields to the horse CSV."""
    qid = str(entity.get("id", ""))
    if not QID.fullmatch(qid):
        raise ValueError("Wikidata entity id must be a Q-id")
    name = _label(entity)
    if not name:
        raise ValueError(f"{qid} has no Japanese or English label")
    external_ids: dict[str, str] = {}
    for property_id, claims in entity.get("claims", {}).items():
        for claim in claims:
            datatype = claim.get("mainsnak", {}).get("datatype")
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if datatype == "external-id" and isinstance(value, str):
                external_ids[property_id] = value
    return {
        "horse_id": qid,
        "horse_name": name,
        "wikidata_id": qid,
        "birth_date": _claim_value(entity, "P569"),
        "sire_wikidata_id": _claim_value(entity, "P22"),
        "dam_wikidata_id": _claim_value(entity, "P25"),
        "external_identifiers_json": json.dumps(external_ids, ensure_ascii=False, sort_keys=True),
        "source_url": f"https://www.wikidata.org/wiki/{qid}",
        "retrieved_at": retrieved_at,
    }


class WikidataHorseClient:
    """Small-batch Action API client with a local cache, spacing and backoff."""

    def __init__(
        self,
        cache_dir: str | Path,
        user_agent: str,
        *,
        min_interval_seconds: float = 1.0,
        max_retries: int = 3,
        request_json: Callable[[str, dict[str, str], float], dict[str, Any]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        has_contact = "@" in user_agent or "http://" in user_agent.lower() or "https://" in user_agent.lower()
        if not user_agent or user_agent.lower().startswith(("python", "curl", "urllib")) or not has_contact:
            raise ValueError("A descriptive, contactable Wikidata User-Agent is required")
        self.cache_dir = Path(cache_dir)
        self.user_agent = user_agent
        self.min_interval_seconds = min_interval_seconds
        self.max_retries = max_retries
        self.request_json = request_json or self._request_json
        self.sleep = sleep
        self._last_request_at = 0.0

    def _request_json(self, url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS endpoint
            return json.loads(response.read().decode("utf-8"))

    def _cache_path(self, qid: str) -> Path:
        return self.cache_dir / f"{qid}.json"

    def get_entity(self, qid: str) -> tuple[dict[str, Any], bool]:
        if not QID.fullmatch(qid):
            raise ValueError("Only Wikidata Q-ids may be fetched")
        cache_path = self._cache_path(qid)
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(cached.get("entity"), dict):
                    return cached["entity"], True
            except (OSError, json.JSONDecodeError):
                raise WikidataRequestError(f"Invalid cache file: {cache_path}")

        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            self.sleep(self.min_interval_seconds - elapsed)
        params = urlencode({"action": "wbgetentities", "ids": qid, "props": "labels|claims", "languages": "ja|en", "format": "json", "formatversion": "2", "maxlag": "5"})
        url = f"{ACTION_API}?{params}"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json", "Accept-Encoding": "gzip, deflate"}
        for attempt in range(self.max_retries + 1):
            try:
                self._last_request_at = time.monotonic()
                payload = self.request_json(url, headers, 20.0)
                entity = payload.get("entities", {}).get(qid)
                if not isinstance(entity, dict) or entity.get("missing"):
                    raise WikidataRequestError(f"Wikidata item not found: {qid}")
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps({"cached_at": datetime.now(timezone.utc).isoformat(), "source_url": url, "entity": entity}, ensure_ascii=False), encoding="utf-8")
                return entity, False
            except HTTPError as error:
                retry_after = error.headers.get("Retry-After") if error.headers else None
                retryable = error.code == 429 or 500 <= error.code < 600
                if not retryable or attempt == self.max_retries:
                    raise WikidataRequestError(f"Wikidata HTTP {error.code}") from error
                self.sleep(float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt)
            except (URLError, TimeoutError, json.JSONDecodeError) as error:
                if attempt == self.max_retries:
                    raise WikidataRequestError("Wikidata request failed; no partial CSV was written") from error
                self.sleep(2 ** attempt)
        raise AssertionError("unreachable")


def import_wikidata_horses(
    qids: list[str], output_path: str | Path, *, cache_dir: str | Path, user_agent: str,
    rights_manifest: str | Path, provider_id: str = "wikidata-cc0",
    client: WikidataHorseClient | None = None,
) -> Path:
    """Fetch requested horse items only after verifying the CC0 rights ledger."""
    if not qids or len(set(qids)) != len(qids):
        raise ValueError("Provide one or more unique Wikidata Q-ids")
    provider = verify_provider_rights(rights_manifest, provider_id, "horses", {"ingest", "internal_storage"})
    active_client = client or WikidataHorseClient(cache_dir, user_agent)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows = [map_horse_entity(active_client.get_entity(qid)[0], retrieved_at) for qid in qids]
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(target, index=False)
    sidecar = write_provenance(target, input_path=target, rights_manifest=rights_manifest, provider=provider, record_type="horses", purposes={"ingest", "internal_storage"}, row_count=len(rows))
    provenance = json.loads(sidecar.read_text(encoding="utf-8"))
    provenance.update({"source_kind": "Wikidata Action API", "api_endpoint": ACTION_API, "requested_qids": qids, "cache_dir": str(Path(cache_dir)), "api_policy": "human-operated; cache-first; one request per second; bounded retry/backoff"})
    sidecar.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
