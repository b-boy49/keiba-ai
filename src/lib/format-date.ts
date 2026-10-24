const weekdays = ["日", "月", "火", "水", "木", "金", "土"];

// "2026-11-07" 形式の日付を実行環境のタイムゾーンに依存せず分解する
export function parseIsoDate(date: string) {
  const [year, month, day] = date.split("-").map(Number);
  return { year, month, day, weekday: weekdays[new Date(Date.UTC(year, month - 1, day)).getUTCDay()] };
}

/** 2026年11月7日(土) */
export function formatJaDate(date: string) {
  const d = parseIsoDate(date);
  return `${d.year}年${d.month}月${d.day}日(${d.weekday})`;
}

/** 2026.11.7（土） */
export function formatDotDate(date: string) {
  const d = parseIsoDate(date);
  return `${d.year}.${d.month}.${d.day}（${d.weekday}）`;
}
