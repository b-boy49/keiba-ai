"""Generate an offline, rights-gated presentation demo from fixed research results."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

import pandas as pd

from .all_dirt_research import _splits
from .data import load_authorized_training_csv
from .training import load_bundle, predict

DEMO_RACE_COUNT = 4
EVALUATION = {"top1_rate": 22.15, "top3_rate": 48.73, "races": 158}
WITHHELD_NAME = "馬名非表示（独立確認待ち）"


def _local_quarantine(path: str | Path) -> Path:
    value, root = Path(path).resolve(), Path("ai/quarantine").resolve()
    if value != root and root not in value.parents:
        raise PermissionError("Presentation demo artifacts must remain under ai/quarantine")
    return value


def select_demo_races(test: pd.DataFrame, count: int = DEMO_RACE_COUNT) -> list[str]:
    """Fixed earliest held-out races; selection does not inspect predictions/results."""
    dates = test[["race_id", "race_date"]].drop_duplicates().sort_values(["race_date", "race_id"])
    ids = dates["race_id"].astype(str).tolist()[:count]
    if len(ids) != count:
        raise ValueError(f"At least {count} held-out races are required")
    return ids


def _reason(row: pd.Series, race: pd.DataFrame) -> str:
    """Explain only pre-race feature comparisons in plain Japanese."""
    parts: list[str] = []
    recent = pd.to_numeric(race["recent_finish_avg"], errors="coerce")
    if pd.notna(row["recent_finish_avg"]) and row["recent_finish_avg"] <= recent.median():
        parts.append("直近の着順傾向が、このレースの出走馬の中で比較的良好")
    dirt = pd.to_numeric(race["dirt_2100_finish_avg"], errors="coerce").replace(0, pd.NA)
    if float(row.get("dirt_2100_finish_avg", 0) or 0) > 0 and row["dirt_2100_finish_avg"] <= dirt.median():
        parts.append("ダート2100mでの過去成績が、このレースの出走馬の中で比較的良好")
    if int(row.get("tokyo_starts", 0) or 0) > 0:
        parts.append("東京競馬場での出走経験がある")
    jockey = pd.to_numeric(race["jockey_win_rate"], errors="coerce")
    if float(row.get("jockey_win_rate", 0) or 0) >= jockey.median():
        parts.append("騎手の過去勝率が、このレースの出走馬の中で比較的高い")
    return "・".join(parts[:2]) or "複数のレース前情報を総合して評価"


def _load_verified_names(path: str | Path, selected: pd.DataFrame) -> dict[tuple[str, str], str]:
    mapping = pd.read_csv(path, dtype=str).fillna("")
    required = {"race_id", "horse_id", "horse_name", "source_url", "confirmed_at", "verification_status", "display_scope"}
    if missing := required - set(mapping.columns):
        raise ValueError(f"Horse-name mapping misses: {', '.join(sorted(missing))}")
    if not mapping["verification_status"].eq("CONFIRMED").all() or not mapping["display_scope"].eq("LOCAL_PRESENTATION").all():
        raise PermissionError("Only confirmed, local-presentation name records may be displayed")
    if not mapping["source_url"].str.startswith("https://www.jra.go.jp/").all():
        raise PermissionError("Horse-name mappings must cite an independently checked JRA official source")
    pd.to_datetime(mapping["confirmed_at"], utc=True, errors="raise")
    if mapping.duplicated(["race_id", "horse_id"]).any():
        raise ValueError("Horse-name mapping contains duplicate race/horse pairs")
    allowed = set(zip(selected["race_id"].astype(str), selected["horse_id"].astype(str)))
    rows = mapping.loc[mapping.apply(lambda row: (row["race_id"], row["horse_id"]) in allowed, axis=1)]
    return {(row.race_id, row.horse_id): row.horse_name for row in rows.itertuples(index=False)}


def _name(row: pd.Series, names: dict[tuple[str, str], str]) -> str:
    return names.get((str(row["race_id"]), str(row["horse_id"])), WITHHELD_NAME)


def _evaluation_summary(metadata: dict) -> dict[str, float | int | str]:
    metrics = metadata.get("test_metrics", {}).get("model", {})
    actual = (round(float(metrics.get("winner_top1_accuracy")) * 100, 2), round(float(metrics.get("winner_top3_recall")) * 100, 2), int(metrics.get("races")))
    expected = (EVALUATION["top1_rate"], EVALUATION["top3_rate"], EVALUATION["races"])
    if actual != expected:
        raise ValueError("Research evaluation metadata does not match the fixed presentation summary")
    return {**EVALUATION, "scope": "東京ダート2100mの時系列テスト"}


def _outcome(predicted: list[dict], actual: list[dict]) -> dict[str, bool]:
    winner = next((x["horse_name"] for x in actual if x["finish_position"] == 1), None)
    names = {x["horse_name"] for x in predicted}
    return {"top1_winner": bool(predicted and predicted[0]["actual_finish"] == 1), "winner_in_top3": winner in names, "top3_finish": any(x["actual_finish"] <= 3 for x in predicted)}


def _render_html(report: dict) -> str:
    """Standalone dashboard; it embeds data and makes no network request."""
    data = json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KEIBA AI | 過去レース予想デモ</title><style>
:root{{--bg:#031d17;--panel:#063326;--ink:#f3f1e8;--muted:#b6c5b8;--gold:#ebca6e;--line:rgba(235,202,110,.38)}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at 92% 0,rgba(163,120,29,.19),transparent 32%),radial-gradient(ellipse at 4% 50%,rgba(29,103,64,.28),transparent 39%),var(--bg);color:var(--ink);font-family:"Noto Serif JP","Yu Mincho",serif;line-height:1.55}}button{{font:inherit;color:inherit}}.shell{{width:min(1160px,calc(100% - 48px));margin:auto}}.hero{{padding:42px 0 32px;border-bottom:1px solid var(--line);background:linear-gradient(110deg,rgba(0,25,20,.96),rgba(3,43,32,.75))}}.brand{{font:700 clamp(30px,4vw,42px)/1 Georgia,serif;letter-spacing:1px}}.brand i{{color:var(--gold);font-style:normal}}.eyebrow{{margin:18px 0 5px;color:var(--gold);font:700 11px Arial,sans-serif;letter-spacing:1.7px}}h1{{margin:0;font-size:clamp(27px,4vw,43px);letter-spacing:.08em}}.intro{{max-width:760px;margin:10px 0 0;color:var(--muted);font-size:14px}}.summary{{display:grid;grid-template-columns:1.3fr repeat(3,1fr);gap:12px;margin:22px auto}}.metric,.guide,.race-panel{{border:1px solid var(--line);border-radius:13px;background:linear-gradient(135deg,rgba(7,54,40,.96),rgba(2,30,23,.94));box-shadow:0 12px 28px rgba(0,0,0,.18)}}.metric{{padding:16px 18px}}.metric small{{display:block;color:var(--muted);font-size:11px}}.metric b{{display:block;margin-top:2px;color:var(--gold);font:700 clamp(23px,3vw,31px)/1.2 Georgia,serif}}.metric.scope b{{font-size:16px;line-height:1.45;color:var(--ink)}}.tabs{{display:flex;gap:9px;overflow:auto;padding:3px 0 13px;scrollbar-width:thin}}.tab{{flex:0 0 auto;border:1px solid rgba(235,202,110,.42);border-radius:8px;background:#062c22;padding:10px 14px;cursor:pointer;font-size:13px}}.tab[aria-selected="true"]{{background:linear-gradient(135deg,#d7b557,#87651c);border-color:#f6dd8a;color:#112219;font-weight:700}}.race-panel{{overflow:hidden}}.race-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;padding:22px 26px;border-bottom:1px solid rgba(235,202,110,.25)}}.race-head h2{{margin:2px 0;font-size:clamp(23px,3vw,31px)}}.race-meta{{color:var(--muted);font:12px Arial,sans-serif}}.local{{border:1px solid var(--gold);border-radius:999px;color:#f5d87d;padding:5px 9px;font:700 10px Arial,sans-serif;letter-spacing:1px}}.outcomes{{display:flex;flex-wrap:wrap;gap:8px;padding:15px 26px;background:rgba(0,13,10,.27)}}.outcome{{border-radius:999px;padding:6px 10px;font:700 11px Arial,sans-serif}}.hit{{background:rgba(75,172,107,.2);border:1px solid rgba(102,189,133,.7);color:#baf2cb}}.miss{{background:rgba(201,101,84,.15);border:1px solid rgba(224,134,118,.5);color:#ffc1b5}}.grid{{display:grid;grid-template-columns:1.55fr 1fr}}.predictions,.actuals{{padding:24px 26px}}.actuals{{border-left:1px solid rgba(235,202,110,.22);background:rgba(0,15,12,.18)}}h3{{margin:0 0 14px;font-size:16px;color:#f6dc90}}ol{{list-style:none;padding:0;margin:0}}.prediction{{display:grid;grid-template-columns:38px minmax(0,1fr);gap:13px;padding:13px;margin-bottom:9px;border-radius:9px;background:rgba(255,255,255,.045)}}.medal{{display:grid;place-items:center;width:31px;height:31px;border-radius:50%;font:bold 14px Arial,sans-serif}}.gold{{background:linear-gradient(135deg,#fae497,#ae7520);color:#263022}}.silver{{background:linear-gradient(135deg,#eff3ef,#899991);color:#19231e}}.bronze{{background:linear-gradient(135deg,#e2a66d,#89552d);color:#fff}}.horse{{display:block;font-size:19px;line-height:1.25;word-break:break-word}}.finish{{display:block;margin-top:3px;color:var(--muted);font-size:12px}}.finish strong{{color:var(--gold);font-size:18px}}.reason{{margin:7px 0 0;color:#e0e9df;font-size:13px;overflow-wrap:anywhere}}.actual{{display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid rgba(235,241,234,.12)}}.actual:last-child{{border:0}}.place{{min-width:26px;color:var(--gold);font:bold 15px Arial,sans-serif}}.actual .horse{{font-size:17px}}.navigation{{display:flex;justify-content:space-between;gap:10px;padding:18px 26px;border-top:1px solid rgba(235,202,110,.22)}}.nav{{border:1px solid var(--line);border-radius:8px;background:#083629;padding:9px 13px;cursor:pointer;font-size:13px}}.nav:disabled{{opacity:.35;cursor:not-allowed}}.guide{{margin:20px 0 42px;padding:22px 26px}}.guide h2{{margin:0 0 8px;font-size:21px;color:var(--gold)}}.guide p{{margin:7px 0;color:#dce6dc;font-size:14px}}.notice{{color:var(--muted)!important;font-size:12px!important}}footer{{border-top:1px solid var(--line);padding:20px 0 34px;color:var(--muted);font:11px Arial,sans-serif}}@media(max-width:820px){{.summary{{grid-template-columns:repeat(2,1fr)}}.metric.scope{{grid-column:span 2}}.grid{{grid-template-columns:1fr}}.actuals{{border-left:0;border-top:1px solid rgba(235,202,110,.22)}}}}@media(max-width:560px){{.shell{{width:auto;margin-left:14px;margin-right:14px}}.hero{{padding:31px 0 25px}}.summary{{grid-template-columns:1fr 1fr;gap:8px}}.metric{{padding:13px}}.metric.scope{{grid-column:span 2}}.race-head,.predictions,.actuals,.navigation{{padding-left:16px;padding-right:16px}}.race-head{{display:block}}.local{{display:inline-block;margin-top:10px}}.outcomes{{padding:12px 16px}}.prediction{{padding:11px;gap:10px}}.horse{{font-size:17px}}.guide{{padding:18px 16px}}}}</style></head><body><main>
<header class="hero"><div class="shell"><div class="brand">KEIBA <i>AI</i></div><p class="eyebrow">PRESENTATION MODE · LOCAL RESEARCH DEMO</p><h1>過去レース AI予想デモ</h1><p class="intro">予測時点より前に得られた情報だけで、AIが上位候補を並べた記録です。</p></div></header>
<section class="shell summary" aria-label="検証済みAI精度サマリー"><div class="metric scope"><small>評価対象</small><b>東京ダート2100mの時系列テスト</b></div><div class="metric"><small>Top1 勝ち馬予測率</small><b id="metric-top1"></b></div><div class="metric"><small>Top3 候補内勝ち馬率</small><b id="metric-top3"></b></div><div class="metric"><small>評価レース数</small><b id="metric-races"></b></div></section><section class="shell"><div id="tabs" class="tabs" role="tablist" aria-label="デモレースを選択"></div><section id="race" class="race-panel" aria-live="polite"></section></section>
<section class="shell guide"><h2>AIは何を見ている？</h2><p>過去の着順、同じ距離での走り、東京競馬場での経験、騎手の過去成績などを参考に、出走馬ごとの上位候補を考えます。</p><p>レース結果や、その後に分かった情報は予測には使っていません。AIの予想は必ず当たるものではありません。</p><p class="notice">この画面は研究用モデルによるローカル発表会専用デモです。一般公開モデルではなく、外部サイト・API・CDNには接続しません。4レースの表示結果を、158レース全体の評価と混同しないでください。</p></section></main><footer><div class="shell">LOCAL INTERNAL ONLY · 馬名はJRA公式情報との独立照合が確認済みの18件だけを表示しています。未確認馬名は非表示です。</div></footer>
<script id="demo-data" type="application/json">{data}</script><script>(() => {{const report=JSON.parse(document.getElementById('demo-data').textContent);let current=0;document.getElementById('metric-top1').textContent=report.evaluation.top1_rate.toFixed(2)+'%';document.getElementById('metric-top3').textContent=report.evaluation.top3_rate.toFixed(2)+'%';document.getElementById('metric-races').textContent=report.evaluation.races+' レース';const esc=value=>String(value).replace(/[&<>"']/g,char=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[char]));const label=(hit,yes,no)=>`<span class="outcome ${{hit?'hit':'miss'}}">${{hit?yes:no}}</span>`;function render(){{const race=report.races[current];document.getElementById('tabs').innerHTML=report.races.map((item,index)=>`<button class="tab" role="tab" aria-selected="${{index===current}}" aria-controls="race" data-index="${{index}}">${{esc(item.race_date)}}・${{item.race_number}}R</button>`).join('');const top=race.predicted_top3.map(item=>`<li class="prediction"><span class="medal ${{['gold','silver','bronze'][item.predicted_rank-1]}}">${{item.predicted_rank}}</span><div><b class="horse">${{esc(item.horse_name)}}</b><span class="finish">実際の着順 <strong>${{item.actual_finish}}着</strong></span><p class="reason">${{esc(item.reason)}}</p></div></li>`).join('');const actual=race.actual_top3.map(item=>`<li class="actual"><span class="place">${{item.finish_position}}着</span><b class="horse">${{esc(item.horse_name)}}</b></li>`).join('');const o=race.outcome;document.getElementById('race').innerHTML=`<header class="race-head"><div><p class="eyebrow">東京 ダート ${{race.distance_m}}m · 過去レース</p><h2>${{esc(race.race_date)}}　${{race.race_number}}R</h2><div class="race-meta">レースID ${{esc(race.race_id)}}　｜　出走 ${{race.field_size}}頭</div></div><span class="local">LOCAL ONLY</span></header><div class="outcomes">${{label(o.top1_winner,'本命的中','本命不的中')}}${{label(o.winner_in_top3,'勝ち馬候補的中','勝ち馬候補不的中')}}${{label(o.top3_finish,'3着以内あり','3着以内なし')}}</div><div class="grid"><article class="predictions"><h3>AI予想 上位3頭</h3><ol>${{top}}</ol></article><aside class="actuals"><h3>実際の上位3頭</h3><ol>${{actual}}</ol></aside></div><nav class="navigation" aria-label="レース切り替え"><button class="nav" id="previous" ${{current===0?'disabled':''}}>← 前のレース</button><button class="nav" id="next" ${{current===report.races.length-1?'disabled':''}}>次のレース →</button></nav>`;document.querySelectorAll('.tab').forEach(button=>button.addEventListener('click',()=>{{current=Number(button.dataset.index);render();}}));document.getElementById('previous').addEventListener('click',()=>{{current-=1;render();}});document.getElementById('next').addEventListener('click',()=>{{current+=1;render();}});}}render();}})();</script></body></html>'''


def create_presentation_demo(*, input_path: str | Path, model_dir: str | Path, output_dir: str | Path, rights_manifest: str | Path, provider_id: str, horse_name_mapping: str | Path | None = None, include_horse_names: bool = False) -> Path:
    """Create JSON + standalone HTML; never publishes or changes the selected model."""
    root, model = _local_quarantine(output_dir), _local_quarantine(model_dir)
    frame = load_authorized_training_csv(input_path)
    frame["race_date"] = pd.to_datetime(frame["race_date"], utc=True, errors="raise")
    metadata = load_bundle(model)["metadata"]
    if metadata.get("visibility") != "internal research only; never publish":
        raise PermissionError("Only an explicitly internal research model may be used for this demo")
    if include_horse_names and not horse_name_mapping:
        raise ValueError("--include-horse-names requires --horse-name-mapping")
    _, _, test, _ = _splits(frame)
    race_ids = select_demo_races(test)
    cohort = test.loc[test["race_id"].astype(str).isin(race_ids)].copy()
    prediction = predict(load_bundle(model), cohort)
    enriched = cohort.merge(prediction[["race_id", "horse_id", "predicted_rank", "reference_win_score"]], on=["race_id", "horse_id"], validate="one_to_one")
    names = _load_verified_names(horse_name_mapping, enriched) if include_horse_names else {}
    races = []
    for race_id in race_ids:
        race = enriched.loc[enriched["race_id"].astype(str).eq(race_id)].copy()
        predicted = [{"predicted_rank": int(row.predicted_rank), "horse_name": _name(pd.Series(row._asdict()), names), "actual_finish": int(row.finish_position), "prediction_score": float(row.reference_win_score) if pd.notna(row.reference_win_score) else None, "reason": _reason(pd.Series(row._asdict()), race)} for row in race.sort_values("predicted_rank").head(3).itertuples(index=False)]
        actual = [{"finish_position": int(row.finish_position), "horse_name": _name(pd.Series(row._asdict()), names)} for row in race.sort_values("finish_position").head(3).itertuples(index=False)]
        races.append({"race_id": race_id, "race_date": race["race_date"].iloc[0].date().isoformat(), "race_number": int(str(race_id)[-2:]), "distance_m": 2100, "field_size": int(len(race)), "predicted_top3": predicted, "actual_top3": actual, "outcome": _outcome(predicted, actual)})
    root.mkdir(parents=True, exist_ok=True)
    all_pairs = enriched[["race_id", "horse_id"]].astype(str).drop_duplicates()
    all_pairs["verification_status"] = ["CONFIRMED" if (row.race_id, row.horse_id) in names else "UNCONFIRMED" for row in all_pairs.itertuples(index=False)]
    all_pairs.loc[all_pairs["verification_status"].eq("UNCONFIRMED")].to_csv(root / "unconfirmed-horse-names.csv", index=False)
    report = {"schema_version": 2, "visibility": "LOCAL_INTERNAL_ONLY", "name_display": "OFFICIAL_SOURCE_CONFIRMED" if include_horse_names else "WITHHELD", "selection": {"cohort": "chronological untouched Tokyo dirt 2100m test cohort", "rule": f"first {DEMO_RACE_COUNT} races by date and race ID; selection does not inspect results or predictions", "race_ids": race_ids}, "leakage_controls": {"feature_as_of": "each race date before same-day results are applied", "excluded_from_features": ["finish_position", "time", "finalt", "time_factor"], "model_tuning": "Validation only; this test cohort was not used for selection"}, "model": {"version": metadata["version"], "approval": metadata.get("approval"), "publication_permitted": False}, "evaluation": _evaluation_summary(metadata), "display_limitations": "Names are sourced only from the independently verified JRA allowlist and are limited to local presentation. No research-dataset name is displayed or exported.", "races": races}
    (root / "presentation-demo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "presentation-demo.html").write_text(_render_html(report), encoding="utf-8")
    return root / "presentation-demo.html"
