"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { RaceStatus } from "./RaceStatus";
import { surfaceLabel, type Race } from "@/types/race";
import { parseIsoDate } from "@/lib/format-date";

const calendarDates = ["2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07", "2026-11-08", "2026-11-09"];
const courses = [{ id: "all", name: "すべて" }, { id: "tokyo", name: "東京" }, { id: "kyoto", name: "京都" }];
const formatDay = (date: string) => parseIsoDate(date);

export function RaceBrowser({ races, initialDate, initialCourse }: { races: Race[]; initialDate?: string; initialCourse?: string }) {
  const [date, setDate] = useState(initialDate && calendarDates.includes(initialDate) ? initialDate : "2026-11-07"); const [course, setCourse] = useState(initialCourse && courses.some((item) => item.id === initialCourse) ? initialCourse : "all"); const [query, setQuery] = useState("");
  const list = useMemo(() => races.filter((race) => race.date === date && (course === "all" || race.courseId === course) && `${race.name} ${race.raceNo}r`.toLowerCase().includes(query.trim().toLowerCase())), [races, date, course, query]);
  return <>
    <section className="calendar-panel" aria-labelledby="calendar-title"><div><p className="section-kicker">RACE CALENDAR</p><h2 id="calendar-title">開催日を選択</h2></div><div className="date-strip" role="list" aria-label="開催日">{calendarDates.map((item) => { const d = formatDay(item); return <button type="button" role="listitem" className={date === item ? "selected" : ""} aria-pressed={date === item} onClick={() => setDate(item)} key={item}><small>11月</small><b>{d.day}</b><span>{d.weekday}</span></button>; })}</div></section>
    <section className="race-filter" aria-label="レース検索条件"><div className="course-tabs" role="group" aria-label="競馬場">{courses.map((item) => <button key={item.id} type="button" onClick={() => setCourse(item.id)} className={course === item.id ? "selected" : ""}>{item.name}</button>)}</div><label className="race-query"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="レース名・レース番号で検索" aria-label="レース名またはレース番号で検索" /></label></section>
    <p className="list-count">{date.replaceAll("-", ".")}　{list.length}件のレース</p>
    {list.length ? <div className="race-list">{list.map((race) => <Link className="race-card" href={`/races/${race.id}`} key={race.id}><div className="race-number"><b>{race.raceNo}</b><span>R</span></div><div className="race-card-main"><div className="card-status"><RaceStatus status={race.status} isDemo={race.isDemo} /></div><h3>{race.name}</h3><p>{race.courseName}競馬場　{race.scheduledStart}発走予定　{surfaceLabel[race.surface]} {race.distanceM.toLocaleString()}m</p><small>{race.className}　／　出馬表発表待ち</small></div><span className="card-arrow" aria-hidden="true">→</span></Link>)}</div> : <div className="no-races" role="status"><span>▦</span><b>開催情報がありません</b><p>選択した開催日・競馬場・検索条件に一致するレースはありません。</p></div>}
  </>;
}
