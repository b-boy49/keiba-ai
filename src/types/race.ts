export type RaceStatus = "SCHEDULED" | "REGISTERED" | "ENTRIES_PUBLISHED" | "DRAW_CONFIRMED" | "IN_PROGRESS" | "RESULT_FINAL" | "POSTPONED" | "CANCELLED" | "DATA_UNAVAILABLE";
export type Surface = "TURF" | "DIRT";

export type Horse = { id: string; name: string; birthDate?: string; sex?: "牡" | "牝" | "せん" };
export type Jockey = { id: string; name: string };
export type RaceEntry = { raceId: string; horse: Horse; jockey?: Jockey; gateNo?: number; horseNo?: number; carriedWeightKg?: number; odds?: number; entryStatus: "REGISTERED" | "CONFIRMED" | "SCRATCHED"; isDemo: boolean };
export type Race = { id: string; date: string; courseId: string; courseName: string; raceNo: number; name: string; scheduledStart: string; surface: Surface; distanceM: number; className: string; status: RaceStatus; source: string; sourceUrl?: string; sourceUpdatedAt: string; isDemo: boolean; entries: RaceEntry[] };

export const raceStatusLabel: Record<RaceStatus, string> = { SCHEDULED: "開催予定", REGISTERED: "登録馬・出走未確定", ENTRIES_PUBLISHED: "出馬表公開", DRAW_CONFIRMED: "枠順確定", IN_PROGRESS: "開催中", RESULT_FINAL: "結果確定", POSTPONED: "延期", CANCELLED: "中止", DATA_UNAVAILABLE: "データ未取得" };
export const surfaceLabel: Record<Surface, string> = { TURF: "芝", DIRT: "ダート" };
