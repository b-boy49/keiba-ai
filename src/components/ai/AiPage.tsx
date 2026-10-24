"use client";

import { useEffect, useState } from "react";
import { BackToHome, SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";
import type { AiPerformance, AiPrediction } from "@/lib/ai/contracts";

type PageKind = "prediction" | "analysis" | "performance";
const raceId = "tokyo-20261107-09";
const headings: Record<PageKind, [string, string]> = {
  prediction: ["AI予想", "確定出馬表と承認済みモデルの情報が揃った場合に、予測を表示します。"],
  analysis: ["AI分析", "予想の根拠となる情報を確認できます。"],
  performance: ["予想成績", "過去の予測と確定結果に基づく記録を表示します。"],
};

function NotReady({ message }: { message: string }) {
  return <div className="ai-empty" role="status"><span>AI STATUS</span><h2>AI予想は準備中です</h2><p>{message}</p><p className="ai-note">確定出馬表、承認済みモデル、許諾済みデータが揃うまでは公開しません。</p></div>;
}

function PredictionCard({ data, analysis }: { data: AiPrediction; analysis: boolean }) {
  return <section className="ai-card"><div className="ai-model-meta"><span>MODEL {data.model_version}</span><span>学習日時: {data.trained_at ?? "確認中"}</span><span>特徴量時点: {data.feature_snapshot_at ?? "確認中"}</span><span>データ出典: {data.data_source}</span></div><h2>{analysis ? "AI予想の根拠" : "レース予想スコア"}</h2>{analysis ? <><p className="ai-description">{data.probability_policy ?? "公開時点の承認済み方針に基づいて表示します。"}</p><p className="ai-note">分析の根拠: {data.predictions[0]?.analysis_basis ?? "レース前までの情報"}</p></> : <ol className="ai-ranking">{data.predictions.map((item) => <li key={item.horse_id}><b>{item.predicted_rank}</b><span>{item.horse_name}</span><em>reference_win_score</em><strong>{item.reference_win_score.toFixed(3)}</strong></li>)}</ol>}<p className="ai-stamp">公開日時: {data.published_at} / 承認日時: {data.approved_at ?? "確認中"}</p></section>;
}

export function AiPage({ kind }: { kind: PageKind }) {
  const [data, setData] = useState<AiPrediction | AiPerformance | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const url = kind === "performance" ? "/api/performance" : `/api/races/${raceId}/${kind === "analysis" ? "analysis" : "prediction"}`;
    fetch(url).then((res) => res.ok ? res.json() : Promise.reject()).then(setData).catch(() => setError(true));
  }, [kind]);
  const [title, intro] = headings[kind];
  const readyPrediction = data?.status === "READY" && kind !== "performance" ? data as AiPrediction : null;
  const readyPerformance = data?.status === "READY" && kind === "performance" ? data as Extract<AiPerformance, { status: "READY" }> : null;
  return <div className="ai-page"><SiteHeader/><main className="shell ai-content"><BackToHome/><p className="section-kicker">KEIBA AI / PHASE 5</p><h1>{title}</h1><p className="ai-intro">{intro}</p>{error ? <NotReady message="データの取得に失敗しました。時間をおいて再度お試しください。"/> : !data ? <div className="ai-empty" aria-live="polite">読み込み中です…</div> : readyPrediction ? <PredictionCard data={readyPrediction} analysis={kind === "analysis"}/> : readyPerformance ? <section className="ai-card"><div className="ai-model-meta"><span>データ出典: {readyPerformance.data_source}</span><span>集計レース数: {readyPerformance.races_evaluated}</span></div><h2>確定結果に基づく記録</h2><div className="ai-performance"><div><small>1着予測的中数</small><b>{readyPerformance.top1_winner_hits}</b></div><div><small>1着予測的中率</small><b>{readyPerformance.top1_winner_rate === null ? "算出不可" : `${(readyPerformance.top1_winner_rate * 100).toFixed(1)}%`}</b></div></div><p className="ai-stamp">集計日時: {readyPerformance.published_at}</p></section> : <NotReady message={(data as { message: string }).message}/>}</main><SiteFooter/></div>;
}
