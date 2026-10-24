from __future__ import annotations

import argparse, json
from pathlib import Path
import pandas as pd
from .data import import_entity_csv, import_licensed_csv, load_authorized_training_csv, read_race_csv
from .synthetic import make_synthetic_races
from .training import evaluate_scores, load_bundle, predict, train_candidate
from .registry import approve_candidate, compare_candidates
from .publish import publish_prediction_snapshot, publish_performance_snapshot
from .rights import write_prediction_provenance
from .target_race import build_target_features
from .wikidata import import_wikidata_horses
from .sqlite_inspection import write_inspection_report
from .kblueleaf_converter import convert_kblueleaf_all_dirt, convert_kblueleaf_tokyo_dirt_2100
from .research_evaluation import generate_research_evaluation
from .all_dirt_research import run_all_dirt_research
from .target_intake import import_post_2025_results, history_coverage_report, predict_target_research
from .presentation_demo import create_presentation_demo
from .target_watch import run_target_watch
from .canonical_identity import resolve_race_card_identities
from .race_prediction import build_race_features, predict_configured_race_research, race_history_coverage_report
from .live_race_dashboard import create_live_race_dashboard
from .historical_full_ranking import rerun_historical_full_rankings

def rights_args(command: argparse.ArgumentParser) -> None:
    command.add_argument("--rights-manifest", required=True); command.add_argument("--provider-id", required=True)

def main() -> None:
    parser = argparse.ArgumentParser(description="KEIBA AI model foundation; external access is human-operated only"); commands = parser.add_subparsers(dest="command", required=True)
    synthetic = commands.add_parser("make-synthetic"); synthetic.add_argument("--output", required=True); synthetic.add_argument("--races", type=int, default=90)
    importer = commands.add_parser("import-csv"); importer.add_argument("--input", required=True); importer.add_argument("--output", required=True); importer.add_argument("--source-name", required=True); importer.add_argument("--rights-confirmed", action="store_true"); rights_args(importer)
    entity = commands.add_parser("import-entity-csv"); entity.add_argument("--input", required=True); entity.add_argument("--output", required=True); entity.add_argument("--record-type", required=True); rights_args(entity)
    wikidata = commands.add_parser("import-wikidata-horses", help="Fetch explicitly supplied Wikidata Q-ids into a rights-tracked horse CSV")
    wikidata.add_argument("--qid", action="append", required=True); wikidata.add_argument("--output", required=True); wikidata.add_argument("--cache-dir", default="ai/cache/wikidata"); wikidata.add_argument("--user-agent", required=True); wikidata.add_argument("--rights-manifest", required=True); wikidata.add_argument("--provider-id", default="wikidata-cc0")
    sqlite_inspect = commands.add_parser("inspect-racing-sqlite", help="Read-only inspection for a quarantined Race/Horse SQLite file")
    sqlite_inspect.add_argument("--input", required=True); sqlite_inspect.add_argument("--output", required=True)
    identity_review = commands.add_parser("resolve-race-card-identities", help="Create exact-match canonical-ID review CSV from a read-only research SQLite master")
    identity_review.add_argument("--entries", required=True); identity_review.add_argument("--sqlite", required=True); identity_review.add_argument("--output", required=True)
    kblueleaf = commands.add_parser("convert-kblueleaf-tokyo-dirt-2100", help="Create chronological research-only features from a quarantined database")
    kblueleaf.add_argument("--input", required=True); kblueleaf.add_argument("--output", required=True)
    all_dirt = commands.add_parser("convert-kblueleaf-all-dirt", help="Create chronological research-only features for every dirt race")
    all_dirt.add_argument("--input", required=True); all_dirt.add_argument("--output", required=True)
    all_dirt.add_argument("--min-distance", type=int, default=0); all_dirt.add_argument("--max-distance", type=int, default=9999)
    research_report = commands.add_parser("research-evaluation", help="Create an internal benchmark and prediction-vs-result report")
    research_report.add_argument("--input", required=True); research_report.add_argument("--model", required=True); research_report.add_argument("--output", required=True); research_report.add_argument("--random-trials", type=int, default=200)
    all_dirt_research = commands.add_parser("all-dirt-research", help="Internal-only all-dirt training, tuned on validation and tested on Tokyo dirt 2100m")
    all_dirt_research.add_argument("--input", required=True); all_dirt_research.add_argument("--artifacts", default="ai/quarantine/artifacts")
    target_features = commands.add_parser("build-target-features"); target_features.add_argument("--entries", required=True); target_features.add_argument("--past-performances", required=True); target_features.add_argument("--output", required=True); target_features.add_argument("--feature-as-of", required=True)
    race_features = commands.add_parser("build-race-features", help="Build pre-race features for a configured approved dirt 1800-2200m card")
    race_features.add_argument("--spec", required=True); race_features.add_argument("--entries", required=True); race_features.add_argument("--past-performances", required=True); race_features.add_argument("--output", required=True); race_features.add_argument("--feature-as-of", required=True)
    race_coverage = commands.add_parser("race-history-coverage", help="Report pre-race history gaps for a configured local research race")
    race_coverage.add_argument("--spec", required=True); race_coverage.add_argument("--entries", required=True); race_coverage.add_argument("--past-performances", required=True); race_coverage.add_argument("--output", required=True); race_coverage.add_argument("--feature-as-of", required=True)
    post_2025 = commands.add_parser("import-post-2025-results", help="Rights-checked import of results from 2025-03-01 onward")
    post_2025.add_argument("--input", required=True); post_2025.add_argument("--output", required=True); post_2025.add_argument("--horses", required=True); post_2025.add_argument("--jockeys", required=True); rights_args(post_2025)
    coverage = commands.add_parser("target-history-coverage", help="Report missing or stale history for target entries")
    coverage.add_argument("--entries", required=True); coverage.add_argument("--past-performances", required=True); coverage.add_argument("--output", required=True); coverage.add_argument("--feature-as-of", required=True)
    target_predict = commands.add_parser("predict-target-research", help="Internal-only quarantined Top-3 target prediction")
    target_predict.add_argument("--entries", required=True); target_predict.add_argument("--past-performances", required=True); target_predict.add_argument("--horses", required=True); target_predict.add_argument("--jockeys", required=True); target_predict.add_argument("--model", required=True); target_predict.add_argument("--registry", default="ai/quarantine/research-active.json"); target_predict.add_argument("--output", required=True); target_predict.add_argument("--feature-as-of", required=True)
    race_predict = commands.add_parser("predict-configured-race-research", help="Rank every confirmed runner for the configured local research race")
    race_predict.add_argument("--spec", required=True); race_predict.add_argument("--entries", required=True); race_predict.add_argument("--past-performances", required=True); race_predict.add_argument("--horses", required=True); race_predict.add_argument("--jockeys", required=True); race_predict.add_argument("--model", required=True); race_predict.add_argument("--registry", default="ai/quarantine/research-active.json"); race_predict.add_argument("--output", required=True); race_predict.add_argument("--feature-as-of", required=True)
    dashboard = commands.add_parser("create-live-race-dashboard", help="Create an offline configured-race dashboard under quarantine")
    dashboard.add_argument("--spec", required=True); dashboard.add_argument("--output", required=True); dashboard.add_argument("--entries"); dashboard.add_argument("--prediction"); dashboard.add_argument("--model-version"); dashboard.add_argument("--provider-id")
    historical_rankings = commands.add_parser("rerun-historical-full-rankings", help="Re-run full-field rankings for the fixed untouched 2019 presentation races")
    historical_rankings.add_argument("--input", required=True); historical_rankings.add_argument("--model", required=True); historical_rankings.add_argument("--horse-name-mapping", required=True); historical_rankings.add_argument("--output-dir", required=True)
    watcher = commands.add_parser("watch-target-research", help="Offline approved-CSV watcher; never downloads race data")
    watcher.add_argument("--intake-dir", default="ai/quarantine/intake"); watcher.add_argument("--output-dir", default="ai/quarantine/predictions"); watcher.add_argument("--model", required=True); watcher.add_argument("--registry", default="ai/quarantine/research-active.json"); watcher.add_argument("--feature-as-of", required=True)
    demo = commands.add_parser("create-presentation-demo", help="Create a local-only historical research demo under ai/quarantine")
    demo.add_argument("--input", required=True); demo.add_argument("--model", required=True); demo.add_argument("--output-dir", required=True); demo.add_argument("--rights-manifest", required=True); demo.add_argument("--provider-id", required=True); demo.add_argument("--horse-name-mapping"); demo.add_argument("--include-horse-names", action="store_true")
    train = commands.add_parser("train"); train.add_argument("--input", required=True); train.add_argument("--artifacts", default="ai/artifacts")
    pred = commands.add_parser("predict"); pred.add_argument("--model", required=True); pred.add_argument("--input", required=True); pred.add_argument("--output", required=True)
    evaluate = commands.add_parser("evaluate"); evaluate.add_argument("--predictions", required=True); evaluate.add_argument("--input", required=False)
    retrain = commands.add_parser("retrain"); retrain.add_argument("--input", required=True); retrain.add_argument("--active-metadata"); retrain.add_argument("--artifacts", default="ai/artifacts")
    approve = commands.add_parser("approve"); approve.add_argument("--candidate", required=True); approve.add_argument("--registry", default="ai/artifacts/active.json")
    publish = commands.add_parser("publish-prediction"); publish.add_argument("--registry", default="ai/artifacts/active.json"); publish.add_argument("--predictions", required=True); publish.add_argument("--race-id", required=True); publish.add_argument("--source-name", required=True); publish.add_argument("--rights-confirmed", action="store_true"); publish.add_argument("--output-dir", default="ai/published"); rights_args(publish)
    performance = commands.add_parser("publish-performance"); performance.add_argument("--predictions", required=True); performance.add_argument("--results", required=True); performance.add_argument("--source-name", required=True); performance.add_argument("--rights-confirmed", action="store_true"); performance.add_argument("--output-dir", default="ai/published"); rights_args(performance)
    args = parser.parse_args()
    if args.command == "make-synthetic": print(make_synthetic_races(args.output, races=args.races)); return
    if args.command == "import-csv": print(import_licensed_csv(args.input, args.output, args.source_name, args.rights_confirmed, rights_manifest=args.rights_manifest, provider_id=args.provider_id)); return
    if args.command == "import-entity-csv": print(import_entity_csv(args.input, args.output, record_type=args.record_type, rights_manifest=args.rights_manifest, provider_id=args.provider_id)); return
    if args.command == "import-wikidata-horses": print(import_wikidata_horses(args.qid, args.output, cache_dir=args.cache_dir, user_agent=args.user_agent, rights_manifest=args.rights_manifest, provider_id=args.provider_id)); return
    if args.command == "inspect-racing-sqlite": print(write_inspection_report(args.input, args.output)); return
    if args.command == "resolve-race-card-identities": print(resolve_race_card_identities(entries_path=args.entries, sqlite_path=args.sqlite, output_path=args.output)); return
    if args.command == "convert-kblueleaf-tokyo-dirt-2100": print(convert_kblueleaf_tokyo_dirt_2100(args.input, args.output)); return
    if args.command == "convert-kblueleaf-all-dirt": print(convert_kblueleaf_all_dirt(args.input, args.output, min_distance=args.min_distance, max_distance=args.max_distance)); return
    if args.command == "research-evaluation": print(generate_research_evaluation(args.input, args.model, args.output, random_trials=args.random_trials)); return
    if args.command == "all-dirt-research": print(run_all_dirt_research(args.input, args.artifacts)); return
    if args.command == "build-target-features": print(build_target_features(args.entries, args.past_performances, args.output, args.feature_as_of)); return
    if args.command == "build-race-features": print(build_race_features(spec_path=args.spec, entries_path=args.entries, performances_path=args.past_performances, output_path=args.output, feature_as_of=args.feature_as_of)); return
    if args.command == "race-history-coverage": print(race_history_coverage_report(spec_path=args.spec, entries_path=args.entries, performances_path=args.past_performances, output_path=args.output, feature_as_of=args.feature_as_of)); return
    if args.command == "import-post-2025-results": print(import_post_2025_results(args.input, args.output, horses_path=args.horses, jockeys_path=args.jockeys, provider_id=args.provider_id, rights_manifest=args.rights_manifest)); return
    if args.command == "target-history-coverage": print(history_coverage_report(args.entries, args.past_performances, args.output, args.feature_as_of)); return
    if args.command == "predict-target-research": print(predict_target_research(entries_path=args.entries, performances_path=args.past_performances, horses_path=args.horses, jockeys_path=args.jockeys, model_dir=args.model, registry_path=args.registry, output_path=args.output, feature_as_of=args.feature_as_of)); return
    if args.command == "predict-configured-race-research": print(predict_configured_race_research(spec_path=args.spec, entries_path=args.entries, performances_path=args.past_performances, horses_path=args.horses, jockeys_path=args.jockeys, model_dir=args.model, registry_path=args.registry, output_path=args.output, feature_as_of=args.feature_as_of)); return
    if args.command == "create-live-race-dashboard": print(create_live_race_dashboard(spec_path=args.spec, output_path=args.output, entries_path=args.entries, prediction_path=args.prediction, model_version=args.model_version, provider_id=args.provider_id)); return
    if args.command == "rerun-historical-full-rankings": print(rerun_historical_full_rankings(input_path=args.input, model_dir=args.model, name_allowlist=args.horse_name_mapping, output_dir=args.output_dir)); return
    if args.command == "watch-target-research": print(json.dumps(run_target_watch(intake_dir=args.intake_dir, output_dir=args.output_dir, model_dir=args.model, registry_path=args.registry, feature_as_of=args.feature_as_of), ensure_ascii=False, indent=2)); return
    if args.command == "create-presentation-demo": print(create_presentation_demo(input_path=args.input, model_dir=args.model, output_dir=args.output_dir, rights_manifest=args.rights_manifest, provider_id=args.provider_id, horse_name_mapping=args.horse_name_mapping, include_horse_names=args.include_horse_names)); return
    if args.command in {"train", "retrain"}:
        candidate, metrics = train_candidate(load_authorized_training_csv(args.input), args.artifacts); result = {"candidate": str(candidate), "metrics": metrics.__dict__, "approval": "手動承認が必要です"}
        if args.command == "retrain" and args.active_metadata:
            active = json.loads(Path(args.active_metadata).read_text(encoding="utf-8")); result["comparison"] = compare_candidates(metrics.__dict__, active["metrics"])
        print(json.dumps(result, ensure_ascii=False, indent=2)); return
    if args.command == "predict":
        frame = read_race_csv(args.input, require_outcome=False); bundle = load_bundle(args.model); output = predict(bundle, frame); Path(args.output).parent.mkdir(parents=True, exist_ok=True); output.to_csv(args.output, index=False); write_prediction_provenance(args.output, model_version=bundle["metadata"]["version"], training_provenance=bundle["metadata"].get("dataset_provenance")); print(args.output); return
    if args.command == "evaluate":
        predictions = pd.read_csv(args.predictions)
        if args.input:
            source = load_authorized_training_csv(args.input); merged = predictions.merge(source[["race_id", "horse_id", "finish_position"]], on=["race_id", "horse_id"], how="inner"); print(json.dumps(evaluate_scores(merged, merged["reference_win_score"].to_numpy()).__dict__, ensure_ascii=False, indent=2)); return
        print("評価には --input（確定結果を含む、利用権確認済みCSV）が必要です"); return
    if args.command == "approve": print(approve_candidate(args.candidate, args.registry)); return
    if args.command == "publish-prediction": print(publish_prediction_snapshot(args.registry, args.predictions, args.race_id, args.source_name, args.rights_confirmed, args.output_dir, args.rights_manifest, args.provider_id)); return
    if args.command == "publish-performance": print(publish_performance_snapshot(args.predictions, args.results, args.source_name, args.rights_confirmed, args.output_dir, args.rights_manifest, args.provider_id)); return

if __name__ == "__main__": main()
