"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { api, type TripStatus } from "@/lib/api";
import { useUiStore } from "@/lib/ui-store";
const statuses: Record<TripStatus, string> = {
  IDEA: "灵感",
  PLANNING: "规划中",
  BOOKED: "已预订",
  TRAVELING: "旅途中",
  COMPLETED: "已完成",
  ARCHIVED: "已归档",
};
export default function Trips() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["trips"], queryFn: api.trips });
  const { tripFormOpen, setTripFormOpen } = useUiStore();
  const [formError, setFormError] = useState("");
  const mutation = useMutation({
    mutationFn: api.createTrip,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["trips"] });
      setTripFormOpen(false);
    },
  });
  return (
    <section className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="mb-3 text-xs tracking-widest">TRIPS</p>
          <h1 className="text-3xl">我的旅行</h1>
        </div>
        <Button
          onClick={() => {
            mutation.reset();
            setFormError("");
            setTripFormOpen(true);
          }}
        >
          新建旅行
        </Button>
      </div>
      {tripFormOpen && (
        <form
          className="space-y-5 rounded-xl border border-border bg-white p-6"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const title = String(form.get("title")).trim();
            const start = String(form.get("start"));
            const end = String(form.get("end"));
            if (!title || (start && end && end < start)) {
              setFormError("请填写旅行名称，并确保结束日期不早于开始日期。");
              return;
            }
            setFormError("");
            mutation.mutate({
              title,
              start_date: start || null,
              end_date: end || null,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            });
          }}
        >
          <label className="block text-sm">
            旅行名称
            <input
              autoFocus
              required
              maxLength={200}
              name="title"
              className="mt-2 block w-full rounded-md border border-border p-3"
              placeholder="例如：秋日京都"
            />
          </label>
          <div className="flex flex-wrap gap-5">
            <label className="text-sm">
              开始日期
              <input
                type="date"
                name="start"
                className="mt-2 block rounded-md border border-border p-2"
              />
            </label>
            <label className="text-sm">
              结束日期
              <input
                type="date"
                name="end"
                className="mt-2 block rounded-md border border-border p-2"
              />
            </label>
          </div>
          {(formError || mutation.error) && (
            <p role="alert" className="text-sm text-red-700">
              {formError || mutation.error?.message}
            </p>
          )}
          <div className="flex gap-3">
            <Button disabled={mutation.isPending} type="submit">
              {mutation.isPending ? "保存中…" : "保存旅行"}
            </Button>
            <Button
              variant="outline"
              type="button"
              onClick={() => setTripFormOpen(false)}
            >
              取消
            </Button>
          </div>
        </form>
      )}
      {query.isPending && <p role="status">正在读取旅行…</p>}
      {query.isError && (
        <div role="alert" className="rounded-xl border border-border p-6">
          <p>暂时无法读取旅行，请确认本地 API 已启动。</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => void query.refetch()}
          >
            重试
          </Button>
        </div>
      )}
      {query.data?.length === 0 && (
        <p className="rounded-xl border border-dashed border-border px-8 py-16 text-center opacity-70">
          还没有旅行。记下一次出发，或补录一段回忆。
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        {query.data?.map((trip) => (
          <article
            key={trip.id}
            className="rounded-xl border border-border bg-white p-6"
          >
            <p className="mb-3 text-xs opacity-60">{statuses[trip.status]}</p>
            <h2 className="text-xl">
              <Link className="hover:underline" href={`/trips/${trip.id}`}>
                {trip.title} →
              </Link>
            </h2>
            <p className="mt-4 text-sm opacity-70">
              {trip.start_date ?? "日期待定"}
              {trip.end_date ? ` → ${trip.end_date}` : ""}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
