"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  api,
  type Place,
  type Trip,
  type TripStatus,
  type Visit,
} from "@/lib/api";
import { formatInstant, tripStatuses } from "@/lib/dates";
import { refreshTravel } from "@/lib/queries";
import { Button } from "./ui/button";
import { QueryError } from "./query-error";
import { RecordPlace } from "./record-place";

function VisitRow({ visit, onDelete }: { visit: Visit; onDelete: () => void }) {
  const place = useQuery({
    queryKey: ["place", visit.place_id],
    queryFn: () => api.place(visit.place_id),
  });
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border py-4">
      <div>
        <Link className="text-link" href={`/?place=${visit.place_id}`}>
          {place.data?.canonical_name ?? "查看地点"}
        </Link>
        <p className="muted mt-1">
          {formatInstant(visit.visited_at, place.data?.timezone ?? "UTC")}
          {visit.ended_at &&
            ` → ${formatInstant(visit.ended_at, place.data?.timezone ?? "UTC")}`}
        </p>
        {visit.note && (
          <p className="mt-2 text-sm whitespace-pre-wrap">{visit.note}</p>
        )}
      </div>
      <button className="text-button" onClick={onDelete}>
        删除
      </button>
    </div>
  );
}

function EditTrip({ trip, onDone }: { trip: Trip; onDone: () => void }) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (form: FormData) => {
      const start = String(form.get("start"));
      const end = String(form.get("end"));
      if (start && end && start > end)
        throw new Error("结束日期不能早于开始日期。");
      return api.updateTrip(trip.id, {
        title: String(form.get("title")).trim(),
        status: String(form.get("status")) as TripStatus,
        start_date: start || null,
        end_date: end || null,
        timezone: String(form.get("timezone")).trim(),
        summary: String(form.get("summary")).trim() || null,
      });
    },
    onSuccess: async () => {
      await refreshTravel(client);
      onDone();
    },
  });
  return (
    <form
      className="panel space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate(new FormData(e.currentTarget));
      }}
    >
      <h2 className="text-xl">编辑旅行</h2>
      <label className="field">
        旅行名称
        <input
          name="title"
          required
          maxLength={200}
          defaultValue={trip.title}
        />
      </label>
      <div className="form-grid">
        <label className="field">
          开始日期
          <input
            name="start"
            type="date"
            defaultValue={trip.start_date ?? ""}
          />
        </label>
        <label className="field">
          结束日期
          <input name="end" type="date" defaultValue={trip.end_date ?? ""} />
        </label>
        <label className="field">
          状态
          <select name="status" defaultValue={trip.status}>
            {Object.entries(tripStatuses).map(([key, value]) => (
              <option key={key} value={key}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          旅行时区
          <input
            name="timezone"
            required
            defaultValue={trip.timezone}
            placeholder="Asia/Shanghai"
          />
        </label>
      </div>
      <label className="field">
        旅行简介
        <textarea name="summary" rows={3} defaultValue={trip.summary ?? ""} />
      </label>
      {mutation.error && (
        <p role="alert" className="error-message">
          {mutation.error.message}
        </p>
      )}
      <div className="flex gap-3">
        <Button disabled={mutation.isPending}>保存修改</Button>
        <Button type="button" variant="outline" onClick={onDone}>
          取消
        </Button>
      </div>
    </form>
  );
}

export function TripDetail({
  id,
  startAdding = false,
}: {
  id: string;
  startAdding?: boolean;
}) {
  const client = useQueryClient();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [recording, setRecording] = useState(startAdding);
  const [savedPlace, setSavedPlace] = useState<Place | null>(null);
  const trip = useQuery({
    queryKey: ["trip", id],
    queryFn: () => api.trip(id),
  });
  const visits = useQuery({
    queryKey: ["visits", id],
    queryFn: () => api.visits(id),
  });
  const days = useQuery({
    queryKey: ["days", id],
    queryFn: () => api.days(id),
  });
  const activities = useQuery({
    queryKey: ["activities", id],
    queryFn: () => api.activities(id),
  });
  const action = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: () => refreshTravel(client),
  });
  const addDay = useMutation({
    mutationFn: (form: FormData) =>
      api.createDay(id, {
        date: String(form.get("date")),
        title: String(form.get("title")).trim() || undefined,
      }),
    onSuccess: () => refreshTravel(client),
  });
  const addActivity = useMutation({
    mutationFn: (form: FormData) =>
      api.createActivity(id, {
        trip_day_id: String(form.get("day")),
        title: String(form.get("title")).trim(),
      }),
    onSuccess: () => refreshTravel(client),
  });
  if (trip.isPending) return <p role="status">正在读取旅行…</p>;
  if (trip.error)
    return <QueryError error={trip.error} retry={() => void trip.refetch()} />;
  const t = trip.data;
  return (
    <section className="space-y-6">
      <Link href="/trips" className="text-link">
        ← 我的旅行
      </Link>
      <header className="page-heading">
        <div>
          <p className="eyebrow">TRIP · {tripStatuses[t.status]}</p>
          <h1>{t.title}</h1>
          <p className="muted mt-3">
            {t.start_date ?? "日期待定"}
            {t.end_date && ` → ${t.end_date}`} · {t.timezone}
          </p>
          {t.summary && <p className="mt-3 whitespace-pre-wrap">{t.summary}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setEditing(!editing)}>
            编辑旅行
          </Button>
          <Button onClick={() => setRecording(!recording)}>添加地点</Button>
        </div>
      </header>
      {editing && <EditTrip trip={t} onDone={() => setEditing(false)} />}
      {startAdding && !savedPlace && (
        <div className="panel space-y-3">
          <h2 className="text-xl">旅行已建立，添加本次地点</h2>
          <p className="muted">
            选择到访的城市或区县，确认抵达时间。保存后将自动高亮在“我的世界”，无需重复添加。
          </p>
          <Button
            variant="outline"
            onClick={() => {
              setRecording(false);
              router.replace(`/trips/${id}`);
            }}
          >
            暂不添加，稍后完善
          </Button>
        </div>
      )}
      {savedPlace && (
        <div className="panel space-y-3" role="status">
          <p>已将 {savedPlace.canonical_name} 加入本次旅行，并更新我的世界。</p>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => setRecording(true)}>继续添加下一站</Button>
            <Button asChild variant="outline">
              <Link href={`/?place=${savedPlace.id}`}>查看地图高亮 →</Link>
            </Button>
          </div>
        </div>
      )}
      {recording && (
        <RecordPlace
          tripId={id}
          initialDate={t.start_date}
          onDone={(place) => {
            setRecording(false);
            setSavedPlace(place);
            router.replace(`/trips/${id}`);
          }}
          onCancel={() => setRecording(false)}
        />
      )}
      {action.error && (
        <p role="alert" className="error-message">
          {action.error.message}
        </p>
      )}
      <div className="grid items-start gap-6 xl:grid-cols-2">
        <section className="panel">
          <div className="flex items-center justify-between">
            <h2 className="text-xl">地点与足迹</h2>
            <Link
              className="text-link"
              href={
                visits.data?.[0] ? `/?place=${visits.data[0].place_id}` : "/"
              }
            >
              打开地图 ↗
            </Link>
          </div>
          <p className="muted mt-2">每次到访单独保存，同一地点可以记录多次。</p>
          {visits.isPending && <p className="muted mt-4">正在读取足迹…</p>}
          {visits.error && (
            <QueryError
              error={visits.error}
              retry={() => void visits.refetch()}
            />
          )}
          {visits.data?.length === 0 && (
            <p className="empty-state">还没有地点。添加一次到访或未来行程。</p>
          )}
          {visits.data?.map((v) => (
            <VisitRow
              key={v.id}
              visit={v}
              onDelete={() => {
                if (window.confirm("删除这次访问记录？"))
                  action.mutate(() => api.deleteVisit(v.id));
              }}
            />
          ))}
        </section>
        <section className="panel space-y-5">
          <h2 className="text-xl">每日安排</h2>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.currentTarget;
              addDay.mutate(new FormData(form), {
                onSuccess: () => form.reset(),
              });
            }}
          >
            <div className="form-grid">
              <label className="field">
                行程日期
                <input
                  name="date"
                  type="date"
                  required
                  min={t.start_date ?? undefined}
                  max={t.end_date ?? undefined}
                  defaultValue={t.start_date ?? ""}
                />
              </label>
              <label className="field">
                当天主题（选填）
                <input
                  name="title"
                  maxLength={200}
                  placeholder="例如：沿河漫步"
                />
              </label>
            </div>
            {addDay.error && (
              <p role="alert" className="error-message">
                {addDay.error.message}
              </p>
            )}
            <Button variant="outline" disabled={addDay.isPending}>
              添加一天
            </Button>
          </form>
          {days.error && (
            <QueryError error={days.error} retry={() => void days.refetch()} />
          )}
          {activities.error && (
            <QueryError
              error={activities.error}
              retry={() => void activities.refetch()}
            />
          )}
          {days.data?.map((day) => (
            <article key={day.id} className="border-t border-border pt-4">
              <div className="flex justify-between gap-3">
                <Link className="text-link" href={`/calendar?date=${day.date}`}>
                  {day.date} · {day.title || "自由探索"} ↗
                </Link>
                <button
                  className="text-button"
                  disabled={action.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        "删除这一天及其活动安排？已有访问记录会保留。",
                      )
                    )
                      action.mutate(() => api.deleteDay(day.id));
                  }}
                >
                  删除一天
                </button>
              </div>
              <ul className="mt-3 space-y-2">
                {activities.data
                  ?.filter((a) => a.trip_day_id === day.id)
                  .map((a) => (
                    <li
                      key={a.id}
                      className="flex justify-between gap-3 text-sm"
                    >
                      <span>{a.title}</span>
                      <button
                        className="text-button"
                        disabled={action.isPending}
                        onClick={() => {
                          if (window.confirm("删除这项活动？"))
                            action.mutate(() => api.deleteActivity(a.id));
                        }}
                      >
                        删除
                      </button>
                    </li>
                  ))}
              </ul>
            </article>
          ))}
          {!!days.data?.length && (
            <form
              className="space-y-3 border-t border-border pt-4"
              onSubmit={(e) => {
                e.preventDefault();
                const form = e.currentTarget;
                addActivity.mutate(new FormData(form), {
                  onSuccess: () => form.reset(),
                });
              }}
            >
              <label className="field">
                安排在哪一天
                <select name="day">
                  {days.data.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.date} {d.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                活动名称
                <input
                  name="title"
                  required
                  maxLength={200}
                  placeholder="例如：逛一逛当地市场"
                />
              </label>
              {addActivity.error && (
                <p role="alert" className="error-message">
                  {addActivity.error.message}
                </p>
              )}
              <Button variant="outline" disabled={addActivity.isPending}>
                添加活动
              </Button>
            </form>
          )}
        </section>
      </div>
      <div className="flex justify-end">
        <button
          className="text-button"
          disabled={action.isPending}
          onClick={() => {
            if (
              window.confirm(
                "删除旅行与每日安排？地点及访问记录会保留在地图和日历中。",
              )
            )
              action.mutate(async () => {
                await api.deleteTrip(id);
                router.push("/trips");
              });
          }}
        >
          删除旅行
        </button>
      </div>
    </section>
  );
}
