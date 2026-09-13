"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatInstant, localDate } from "@/lib/dates";
import { Button } from "./ui/button";
import { QueryError } from "./query-error";

export function TravelCalendar() {
  const params = useSearchParams();
  const [selected, setSelected] = useState(() => {
    const value = params.get("date");
    return value &&
      /^(19\d{2}|20\d{2}|2100)-\d{2}-\d{2}$/.test(value) &&
      !Number.isNaN(Date.parse(value)) &&
      new Date(value).toISOString().slice(0, 10) === value
      ? value
      : localDate();
  });
  const [year, month] = selected.split("-").map(Number);
  const query = useQuery({
    queryKey: ["calendar", "month", year, month],
    queryFn: () => api.calendarMonth(year, month),
  });
  const detail = useQuery({
    queryKey: ["calendar", "day", selected],
    queryFn: () => api.calendarDay(selected),
  });
  const firstOffset = (new Date(year, month - 1, 1).getDay() + 6) % 7;
  const total = new Date(year, month, 0).getDate();
  const tripNames = new Map(query.data?.trips.map((t) => [t.id, t.title]));
  const move = (delta: number) => {
    const date = new Date(year, month - 1 + delta, 1);
    if (date.getFullYear() >= 1900 && date.getFullYear() <= 2100)
      setSelected(localDate(date));
  };
  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">TRAVEL CALENDAR</p>
          <h1>把旅行，留在时间里。</h1>
          <p className="muted mt-2">
            旅行日期与地点当地的访问日，共同组成你的旅行日历。
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/trips">管理旅行</Link>
        </Button>
      </div>
      <div className="calendar-layout">
        <section className="panel">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                aria-label="上个月"
                onClick={() => move(-1)}
              >
                ←
              </Button>
              <h2 className="text-xl">
                {year} 年 {month} 月
              </h2>
              <Button
                variant="outline"
                aria-label="下个月"
                onClick={() => move(1)}
              >
                →
              </Button>
            </div>
            <Button variant="outline" onClick={() => setSelected(localDate())}>
              今天
            </Button>
          </div>
          <label className="field mb-4">
            跳转月份
            <input
              type="month"
              min="1900-01"
              max="2100-12"
              value={selected.slice(0, 7)}
              onChange={(e) => {
                if (e.target.value) setSelected(`${e.target.value}-01`);
              }}
            />
          </label>
          {query.isPending && (
            <p className="muted" role="status">
              正在读取日历…
            </p>
          )}
          {query.error && (
            <QueryError
              error={query.error}
              retry={() => void query.refetch()}
            />
          )}
          <div className="calendar-grid">
            {["一", "二", "三", "四", "五", "六", "日"].map((v) => (
              <div className="py-2 text-center text-xs text-stone-500" key={v}>
                {v}
              </div>
            ))}
            {Array.from({ length: firstOffset }, (_, i) => (
              <span key={`blank-${i}`} />
            ))}
            {Array.from({ length: total }, (_, i) => {
              const date = `${year}-${String(month).padStart(2, "0")}-${String(i + 1).padStart(2, "0")}`;
              const cell = query.data?.days.find((d) => d.date === date);
              return (
                <button
                  key={date}
                  className={`calendar-cell ${cell?.trip_ids.length ? "has-trip" : ""} ${date === localDate() ? "today" : ""}`}
                  aria-label={`${date}${cell?.trip_ids.length ? `，${cell.trip_ids.length} 段旅行` : ""}`}
                  aria-pressed={date === selected}
                  onClick={() => setSelected(date)}
                >
                  <span className="text-sm">{i + 1}</span>
                  {cell?.trip_ids.slice(0, 2).map((id) => (
                    <span key={id} className="trip-band">
                      {tripNames.get(id) ?? "旅行"}
                    </span>
                  ))}
                  {cell && cell.trip_ids.length > 2 && (
                    <span className="block text-[10px]">
                      另 {cell.trip_ids.length - 2} 段
                    </span>
                  )}
                  {Boolean(cell?.places_count) && (
                    <span className="block pt-1 text-[10px] text-stone-600">
                      {cell?.places_count} 个地点
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <p className="muted mt-5">
            绿色日期带表示旅行。点击某一天，查看访问与活动。
          </p>
        </section>
        <aside className="space-y-4" aria-label="当天记录" aria-live="polite">
          <p className="eyebrow">DAILY MEMORY</p>
          <h2 className="text-2xl">{selected}</h2>
          {detail.isPending && (
            <p role="status" className="muted">
              正在读取当天记录…
            </p>
          )}
          {detail.error && (
            <QueryError
              error={detail.error}
              retry={() => void detail.refetch()}
            />
          )}
          {detail.data && (
            <>
              {detail.data.trips.map((t) => (
                <Link
                  className="panel block hover:bg-muted"
                  key={t.id}
                  href={`/trips/${t.id}`}
                >
                  <h3>{t.title} →</h3>
                  <p className="muted">
                    {t.start_date ?? "日期待定"}
                    {t.end_date ? ` — ${t.end_date}` : ""}
                  </p>
                </Link>
              ))}
              {detail.data.visits.map((v) => (
                <div key={v.id} className="border-l-2 border-border pl-4">
                  <Link
                    href={`/?place=${v.place_id}`}
                    className="font-medium underline underline-offset-4"
                  >
                    {v.place_name}
                  </Link>
                  <p className="muted">
                    {formatInstant(v.visited_at, v.timezone)}
                  </p>
                  <p className="muted">{v.timezone}</p>
                  {v.note && (
                    <p className="mt-1 text-sm whitespace-pre-wrap">{v.note}</p>
                  )}
                </div>
              ))}
              {detail.data.activities.map((a) => (
                <div key={a.id} className="border-l-2 border-border pl-4">
                  <Link href={`/trips/${a.trip_id}`} className="font-medium">
                    {a.title} →
                  </Link>
                  <p className="muted">
                    {a.place_name ?? "地点待定"}
                    {a.start_at
                      ? ` · ${formatInstant(a.start_at, a.timezone)}`
                      : ""}
                  </p>
                </div>
              ))}
              {!detail.data.trips.length &&
                !detail.data.visits.length &&
                !detail.data.activities.length && (
                  <div className="empty-state">
                    这一天还没有旅行记录。
                    <Link className="mt-4 block underline" href="/">
                      去地图记录一个地方
                    </Link>
                  </div>
                )}
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
