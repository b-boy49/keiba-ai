import Link from "next/link";
import { notFound } from "next/navigation";
import { EntryTable } from "@/components/races/EntryTable";
import { RaceStatus } from "@/components/races/RaceStatus";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { raceRepository } from "@/lib/data-providers";
import { surfaceLabel } from "@/types/race";
import { formatDotDate, formatJaDate } from "@/lib/format-date";

export default async function RaceDetailPage({ params }: { params: Promise<{ raceId: string }> }) {
  const { raceId } = await params; const race = await raceRepository.getById(raceId); if (!race) notFound();
  return <main className="race-page"><header className="subpage-header"><div className="shell"><Link className="sub-brand" href="/"><span>♞</span><b>KEIBA <i>AI</i></b></Link><nav aria-label="パンくず"><Link href="/">ホーム</Link><span>／</span><Link href="/races">レース一覧</Link><span>／</span><b>{race.name}</b></nav></div></header><div className="shell race-content"><Link className="back-link" href="/races">← レース一覧へ戻る</Link><section className="race-hero-card"><div><p className="section-kicker">RACE DETAIL</p><div className="race-title-line"><span className="detail-race-no">{race.raceNo}<small>R</small></span><div><h1>{race.name}</h1><p>{formatDotDate(race.date)}　{race.courseName}競馬場</p></div></div></div><RaceStatus status={race.status} isDemo={race.isDemo} /></section><section className="detail-grid"><article className="detail-panel"><h2>レース情報</h2><dl className="race-spec"><div><dt>開催日</dt><dd>{formatJaDate(race.date)}</dd></div><div><dt>競馬場</dt><dd>{race.courseName}</dd></div><div><dt>発走予定</dt><dd>{race.scheduledStart}</dd></div><div><dt>コース</dt><dd>{surfaceLabel[race.surface]} {race.distanceM.toLocaleString()}m</dd></div><div><dt>条件</dt><dd>{race.className}</dd></div><div><dt>情報元</dt><dd>{race.sourceUrl ? <a href={race.sourceUrl} target="_blank" rel="noreferrer">{race.source}（公式予定）</a> : race.source}</dd></div></dl><p className="updated-note">更新日時：{race.sourceUpdatedAt.slice(0, 10)}　／　番組表は予定です。正式な出馬表は発表後に、利用許諾を確認したCSVから登録します。</p></article><aside className="detail-panel race-actions"><h2>AIメニュー</h2><p>AI分析・AI予想は、出走馬と承認済み実データモデルの情報が揃い次第公開します。</p><Link href="/analysis">AI分析を見る　→</Link><Link href="/predictions">AI予想を見る　→</Link></aside></section><section className="entries-panel"><div className="entries-heading"><div><p className="section-kicker">RACE ENTRIES</p><h2>出馬表</h2></div><RaceStatus status={race.status} isDemo={race.isDemo} /></div><EntryTable entries={race.entries} /></section></div><SiteFooter /></main>;
}
