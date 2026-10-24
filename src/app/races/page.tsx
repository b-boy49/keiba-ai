import { BackToHome, SiteHeader } from "@/components/layout/SiteHeader";
import { RaceBrowser } from "@/components/races/RaceBrowser";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { raceRepository } from "@/lib/data-providers";

export default async function RacesPage({ searchParams }: { searchParams: Promise<{ date?: string | string[]; course?: string | string[] }> }) {
  const { date, course } = await searchParams;
  const races = await raceRepository.list();
  return <main className="race-page"><SiteHeader/><div className="shell race-content"><BackToHome/><div className="page-heading"><p className="section-kicker">RACE FINDER</p><h1>レース一覧</h1><p>開催日・競馬場・レース名から、確認できるレース情報を探せます。</p><span className="demo-note">表示内容は大会資料に基づくデモデータです。公式の開催・出走情報ではありません。</span></div><RaceBrowser races={races} initialDate={typeof date === "string" ? date : undefined} initialCourse={typeof course === "string" ? course : undefined}/></div><SiteFooter/></main>;
}
