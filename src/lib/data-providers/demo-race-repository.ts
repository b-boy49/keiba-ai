import type { Race } from "@/types/race";
import type { RaceRepository, RaceSearch } from "./race-repository";

const demoRaces: Race[] = [{
  id: "tokyo-20261107-09", date: "2026-11-07", courseId: "tokyo", courseName: "東京", raceNo: 9, name: "神奈川新聞杯", scheduledStart: "14:25", surface: "DIRT", distanceM: 2100, className: "3歳以上2勝クラス・定量", status: "SCHEDULED", source: "JRA 開催日程（予定）", sourceUrl: "https://www.jra.go.jp/keiba/calendar2026/2026/11/1107.html", sourceUpdatedAt: "2026-10-23T00:00:00+09:00", isDemo: false, entries: [],
}];

export class DemoRaceRepository implements RaceRepository {
  async list(search: RaceSearch = {}) { const q = search.query?.trim().toLowerCase(); return demoRaces.filter((race) => (!search.date || race.date === search.date) && (!search.courseId || race.courseId === search.courseId) && (!q || `${race.name} ${race.raceNo}r`.toLowerCase().includes(q))); }
  async getById(id: string) { return demoRaces.find((race) => race.id === id) ?? null; }
}
