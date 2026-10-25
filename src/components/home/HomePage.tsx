"use client";

import Link from "next/link";
import { FormEvent, RefObject, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { DataStatusBadge } from "@/components/ui/DataStatusBadge";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { LogoutButton } from "@/components/layout/LogoutButton";
import { HorseMark, Icon, IconName } from "@/app/icons";
import { formatDotDate, formatJaDate } from "@/lib/format-date";
import { raceStatusLabel, surfaceLabel, type Race } from "@/types/race";
import { PresentationOverview } from "@/components/home/PresentationOverview";

const menu: [IconName, string, string][] = [["home", "ホーム", "/"], ["calendar", "レース一覧", "/races"], ["brain", "AI予想", "/predictions"], ["chart", "AI分析", "/analysis"], ["flag", "レース結果", "/results"], ["trophy", "予想成績", "/performance"], ["info", "サイト情報", "/about"]];
const featureCards: [IconName, string, string, string][] = [["calendar", "レース一覧", "開催日・競馬場から\nレースを検索", "/races"], ["brain", "AI予想", "AIによる1〜3着予想と\n根拠を確認", "/predictions"], ["chart", "AI分析", "出走馬の能力や適性を\n多角的に分析", "/analysis"], ["flag", "レース結果", "着順・タイム・払戻金を\nすばやく確認", "/results"], ["trophy", "予想成績", "AI予想の成績や検証を\nチェック", "/performance"]];
const courses = [{ id: "tokyo", name: "東京" }, { id: "kyoto", name: "京都" }];
const featuredRaceId = "tokyo-20261107-09";
// 予想データ未取得のため順位枠だけを表示する（馬名・勝率・グラフは出さない）
const predictionSlots = [["1", "r1"], ["2", "r2"], ["3", "r3"]];

function RaceSearchForm({ races, formRef }: { races: Race[]; formRef: RefObject<HTMLFormElement | null> }) {
  const router = useRouter();
  const dates = useMemo(() => [...new Set(races.map((race) => race.date))].sort(), [races]);
  const initial = races.find((race) => race.id === featuredRaceId) ?? races[0];
  const [date, setDate] = useState(initial?.date ?? dates[0] ?? "");
  const [courseId, setCourseId] = useState(initial?.courseId ?? courses[0].id);
  const matches = useMemo(() => races.filter((race) => race.date === date && race.courseId === courseId).sort((a, b) => a.raceNo - b.raceNo), [races, date, courseId]);
  const [raceId, setRaceId] = useState(initial?.id ?? "");
  // 開催日・競馬場を変えたら、その条件で選べるレースに合わせ直す
  const selectedRaceId = matches.some((race) => race.id === raceId) ? raceId : matches[0]?.id ?? "";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (selectedRaceId) router.push(`/races/${selectedRaceId}`);
    else router.push(`/races?${new URLSearchParams({ date, course: courseId })}`);
  };

  return <form className="race-search" onSubmit={submit} ref={formRef} aria-label="レース検索">
    <label><em>開催日</em><Icon name="calendar" /><select aria-label="開催日" value={date} onChange={(event) => setDate(event.target.value)} disabled={!dates.length}>{dates.length ? dates.map((item) => <option value={item} key={item}>{formatJaDate(item)}</option>) : <option value="">開催情報なし</option>}</select></label>
    <label><em>競馬場</em><Icon name="venue" /><select aria-label="競馬場" value={courseId} onChange={(event) => setCourseId(event.target.value)}>{courses.map((course) => <option value={course.id} key={course.id}>{course.name}</option>)}</select></label>
    <label><em>レース</em><Icon name="list" /><select aria-label="レース" value={selectedRaceId} onChange={(event) => setRaceId(event.target.value)} disabled={!matches.length}>{matches.length ? matches.map((race) => <option value={race.id} key={race.id}>{race.raceNo}R {race.name}</option>) : <option value="">該当レースなし</option>}</select></label>
    <button type="submit"><Icon name="search" /><b>{selectedRaceId ? "レース詳細をみる" : "レース一覧で探す"}</b></button>
  </form>;
}

export function HomePage({ races, localPresentationDemoEnabled = false }: { races: Race[]; localPresentationDemoEnabled?: boolean }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const searchRef = useRef<HTMLFormElement>(null);
  const featured = races.find((race) => race.id === featuredRaceId) ?? races[0];
  const focusSearch = () => { setIsMenuOpen(false); searchRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }); searchRef.current?.querySelector("select")?.focus({ preventScroll: true }); };

  return <main className="home">
    <section className="hero">
      <div className="hero-image" /><div className="hero-shade" />
      <header className="site-header shell">
        <Link className="brand" href="/" aria-label="KEIBA AI ホーム"><HorseMark className="horse-mark" /><span><b>KEIBA <i>AI</i></b><small>AIで読む、競馬の未来</small></span></Link>
        <nav aria-label="主要メニュー">{menu.map(([icon, label, href], index) => <Link href={href} className={index === 0 ? "active" : ""} aria-current={index === 0 ? "page" : undefined} key={label}><Icon name={icon} />{label}</Link>)}</nav>
        <div className="header-actions"><div className="desktop-logout"><LogoutButton /></div><button type="button" className="icon-button search-icon" aria-label="レース検索へ移動" onClick={focusSearch}><Icon name="search" /></button><button type="button" className="icon-button menu-toggle" aria-label={isMenuOpen ? "メニューを閉じる" : "メニューを開く"} aria-expanded={isMenuOpen} aria-controls="mobile-nav" onClick={() => setIsMenuOpen(!isMenuOpen)}><Icon name={isMenuOpen ? "close" : "menu"} /></button></div>
      </header>
      <div className="mobile-logout-bar shell"><LogoutButton /></div>
      {isMenuOpen && <nav id="mobile-nav" className="mobile-nav shell" aria-label="モバイルメニュー">{menu.map(([icon, label, href]) => <Link href={href} key={label} onClick={() => setIsMenuOpen(false)}><Icon name={icon} />{label}</Link>)}<LogoutButton /></nav>}
      <div className="shell hero-content" id="top">
        <p className="hero-script" aria-hidden="true">Predict the Next Winner</p>
        <p className="hero-catch" aria-hidden="true">一瞬の、<br />その先を読む。</p>
        <h1><span className="phrase">AIが導く、</span><br /><span className="phrase">新しい<span className="gold">競馬</span>の</span><span className="phrase">楽しみ方</span></h1>
        <p className="lead"><span className="phrase">過去のデータと最新のAIで、</span><span className="phrase">レースの可能性を分析。</span><br /><span className="phrase">すべての競馬ファンに、</span><span className="phrase">より深く、より楽しい競馬体験を。</span></p>
        <RaceSearchForm races={races} formRef={searchRef} />
      </div>
    </section>
    <PresentationOverview />
    <div className="page-bg">
      {localPresentationDemoEnabled && <section className="shell local-demo-guide" aria-label="Past race AI prediction demo">
        <div><p>LOCAL PRESENTATION MODE</p><h2>過去レース AI予想デモ</h2><span>研究データや予測結果はサイトへ送信されません。発表会用PCで隔離済みHTMLを直接開いてください。</span></div>
        <code>ローカル発表会資料を確認</code>
      </section>}
      <section className="shell feature-grid" aria-label="サービス一覧">{featureCards.map(([icon, title, text, href]) => <Link href={href} className="feature" key={title}><Icon name={icon} className="feature-icon" /><span className="feature-text"><b>{title}</b><small>{text.split("\n").map((line) => <span key={line}>{line}</span>)}</small></span><Icon name="arrow" className="feature-arrow" /></Link>)}</section>
      <section className="shell dashboard">
        <article className="pickup panel"><h2><Icon name="fire" className="h2-icon" /> 本日の注目レース <small>TODAY&apos;S PICKUP</small></h2>
          {featured ? <div className="pickup-photo"><div className="pickup-copy"><div className="race-meta"><time dateTime={featured.date}>{formatDotDate(featured.date)}</time><DataStatusBadge label={featured.entries.length ? raceStatusLabel[featured.status] : "出走馬発表待ち"} /></div><h3>{featured.courseName} {featured.raceNo}R<br />{featured.name}</h3></div><div className="pickup-foot"><p><b>{surfaceLabel[featured.surface]} {featured.distanceM.toLocaleString()}m</b><span>{featured.className}</span><span>発走予定 {featured.scheduledStart}</span></p><Link className="race-cta" href={`/races/${featured.id}`}>レース詳細をみる<Icon name="arrow" /></Link></div></div>
            : <div className="pickup-photo"><div className="pickup-copy"><h3>注目レースは<br />準備中です</h3></div><div className="pickup-foot"><p><span>開催情報を取得でき次第表示します。</span></p><Link className="race-cta" href="/races">レース一覧へ<Icon name="arrow" /></Link></div></div>}
        </article>
        <article className="predictions panel"><div className="panel-head"><h2><Icon name="crown" className="h2-icon" /> AIの予想（上位3頭） <small>AI&apos;s Prediction</small></h2><Link href="/predictions">予想の詳細を見る<Icon name="arrow" /></Link></div>
          <div className="prediction-empty"><ol className="rank-list" aria-label="予想順位（未予測）">{predictionSlots.map(([place, klass]) => <li className="rank" key={place}><span className={`crown ${klass}`}><Icon name="crown" /><i>{place}</i></span><span className="horse-no" aria-hidden="true">—</span><span className="horse-name"><b>{place}着候補　未予測</b><small>出走馬・枠順 未確定</small></span><span className="rate"><span>勝率 <b>—</b></span><i aria-hidden="true" /></span></li>)}</ol>
            <div className="empty-note"><DataStatusBadge label="デモ・未予測" /><p><b>AI予想データ未取得</b>出走馬・枠順・学習済みモデルが未連携のため、予想順位や勝率は表示していません。</p></div></div></article>
      </section>
      <section className="shell news panel"><b><Icon name="megaphone" />お知らせ</b><time>2026.10.23</time><p>トップページの初期デモを公開しました。実データ連携の状況はサイト情報で更新します。</p><Link href="/about">お知らせ一覧<Icon name="arrow" /></Link></section>
    </div>
    <SiteFooter />
  </main>;
}
