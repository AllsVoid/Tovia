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
          <Button onClick={() => setRecording(!recording)}>添加城市</Button>
        </div>
      </header>
      {editing && <EditTrip trip={t} onDone={() => setEditing(false)} />}
      {action.error && (
        <p role="alert" className="error-message">
          {action.error.message}
        </p>
      )}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(260px,0.72fr)_minmax(440px,1.5fr)]">
        <section className="panel space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl">地点与足迹</h2>
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="text-button"
                onClick={() => setRecording(!recording)}
              >
                {recording ? "取消添加" : "＋ 添加城市"}
              </button>
              <Link
                className="text-link"
                href={
                  visits.data?.[0] ? `/?place=${visits.data[0].place_id}` : "/"
                }
              >
                地图 ↗
              </Link>
            </div>
          </div>
          <p className="muted">按城市记录足迹；区县名称会归入所属城市。</p>
          {recording && (
            <div className="border-t border-border pt-4">
              <RecordPlace
                embedded
                tripId={id}
                initialDate={t.start_date}
                onDone={(place) => {
                  setRecording(false);
                  setSavedPlace(place);
                  router.replace(`/trips/${id}`);
                }}
                onCancel={() => {
                  setRecording(false);
                  router.replace(`/trips/${id}`);
                }}
              />
            </div>
          )}
          {savedPlace && !recording && (
            <div
              className="rounded-lg bg-muted px-4 py-3 text-sm"
              role="status"
            >
              <p>{savedPlace.canonical_name} 已加入旅行并更新地图。</p>
              <div className="mt-2 flex flex-wrap gap-4">
                <button
                  className="text-button"
                  onClick={() => setRecording(true)}
                >
                  继续添加城市
                </button>
                <Link className="text-link" href={`/?place=${savedPlace.id}`}>
                  查看地图 →
                </Link>
              </div>
            </div>
          )}
          {startAdding &&
            !recording &&
            !savedPlace &&
            visits.data?.length === 0 && (
              <button
                className="text-button"
                onClick={() => setRecording(true)}
              >
                ＋ 添加第一个城市
              </button>
            )}
          {visits.isPending && <p className="muted">正在读取足迹…</p>}
          {visits.error && (
            <QueryError
              error={visits.error}
              retry={() => void visits.refetch()}
            />
          )}
          {visits.data?.length === 0 && !recording && !savedPlace && (
            <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-[#667360]">
              还没有城市足迹。
            </p>
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
          <div>
            <h2 className="text-xl">每日安排</h2>
            <p className="muted mt-1">先建立旅行日，再直接在当天添加活动。</p>
          </div>
          <form
            className="rounded-xl border border-dashed border-border bg-[#fbfcf8] p-4"
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.currentTarget;
              addDay.mutate(new FormData(form), {
                onSuccess: () => form.reset(),
              });
            }}
          >
            <p className="mb-3 text-sm font-medium">＋ 新建旅行日</p>
            <div className="grid gap-3 md:grid-cols-[minmax(150px,0.8fr)_minmax(200px,1.2fr)_auto] md:items-end">
              <label className="field">
                日期
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
                当天主题
                <input
                  name="title"
                  maxLength={200}
                  placeholder="例如：沿河漫步"
                />
              </label>
              <Button disabled={addDay.isPending}>
                {addDay.isPending ? "添加中…" : "添加一天"}
              </Button>
            </div>
            {addDay.error && (
              <p role="alert" className="error-message">
                {addDay.error.message}
              </p>
            )}
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
          {days.data?.length === 0 && (
            <p className="muted rounded-lg border border-border px-4 py-6 text-center">
              还没有每日安排，从上方添加旅行日开始。
            </p>
          )}
          {days.data?.map((day) => (
            <article
              key={day.id}
              className="rounded-xl border border-border p-4"
            >
              <div className="flex justify-between gap-3">
                <div>
                  <p className="font-medium">{day.date}</p>
                  <Link
                    className="muted text-link"
                    href={`/calendar?date=${day.date}`}
                  >
                    {day.title || "自由探索"} · 打开日历 ↗
                  </Link>
                </div>
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
              <ul className="mt-4 space-y-2">
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
              <form
                className="mt-4 flex flex-wrap items-end gap-2 border-t border-border pt-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget;
                  addActivity.mutate(new FormData(form), {
                    onSuccess: () => form.reset(),
                  });
                }}
              >
                <input type="hidden" name="day" value={day.id} />
                <label className="field min-w-52 flex-1">
                  添加当天活动
                  <input
                    name="title"
                    required
                    maxLength={200}
                    placeholder="例如：逛当地市场"
                  />
                </label>
                <Button variant="outline" disabled={addActivity.isPending}>
                  ＋ 添加活动
                </Button>
              </form>
            </article>
          ))}
          {addActivity.error && (
            <p role="alert" className="error-message">
              {addActivity.error.message}
            </p>
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
