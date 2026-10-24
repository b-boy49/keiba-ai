import type { RaceEntry } from "@/types/race";
export function EntryTable({ entries }: { entries: RaceEntry[] }) {
  if (!entries.length) return <div className="entries-wait" role="status"><span>♞</span><b>出馬表発表待ち</b><p>正式な出走馬、枠順、騎手、斤量、オッズは未発表・未取得です。確認できた情報のみを掲載します。</p></div>;
  return <div className="entry-scroll"><table><caption>出馬表</caption><thead><tr><th scope="col">馬番</th><th scope="col">枠番</th><th scope="col">馬名</th><th scope="col">騎手</th><th scope="col">斤量</th><th scope="col">オッズ</th></tr></thead><tbody>{entries.map((entry) => <tr key={`${entry.raceId}-${entry.horse.id}`}><td>{entry.horseNo ?? "—"}</td><td>{entry.gateNo ?? "—"}</td><td>{entry.horse.name}</td><td>{entry.jockey?.name ?? "—"}</td><td>{entry.carriedWeightKg ? `${entry.carriedWeightKg}kg` : "—"}</td><td>{entry.odds ?? "—"}</td></tr>)}</tbody></table></div>;
}
