"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Place } from "@/lib/api";
import { deviceTimezone, inputToInstant, localDateTime } from "@/lib/dates";
import { refreshTravel } from "@/lib/queries";
import { PlacePicker } from "./place-picker";
import { Button } from "./ui/button";

export function RecordPlace({
  tripId,
  initialPlace = null,
  coordinates,
  onDone,
  onCancel,
}: {
  tripId?: string;
  initialPlace?: Place | null;
  coordinates?: [number, number];
  onDone: () => void;
  onCancel: () => void;
}) {
  const [place, setPlace] = useState<Place | null>(initialPlace);
  const [mode, setMode] = useState<"visit" | "wishlist">("visit");
  const client = useQueryClient();
  const trips = useQuery({
    queryKey: ["trips"],
    queryFn: api.trips,
    enabled: !tripId && mode === "visit",
  });
  const mutation = useMutation({
    mutationFn: async (form: FormData) => {
      if (!place) throw new Error("请先选择地点。");
      const note = String(form.get("note") ?? "").trim();
      if (mode === "wishlist") {
        await api.addWishlist(place.id, note);
        return;
      }
      const start = inputToInstant(String(form.get("start")));
      const endValue = String(form.get("end") ?? "");
      const end = endValue ? inputToInstant(endValue) : null;
      if (end && end < start) throw new Error("离开时间不能早于抵达时间。");
      await api.createVisit({
        place_id: place.id,
        trip_id: tripId ?? (String(form.get("trip") ?? "") || null),
        visited_at: start,
        ended_at: end,
        note: note || null,
      });
    },
    onSuccess: async () => {
      await refreshTravel(client);
      onDone();
    },
  });
  return (
    <section className="panel space-y-5" aria-label="记录地点">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xl">记录一个地方</h2>
        <Button variant="outline" onClick={onCancel}>
          收起
        </Button>
      </div>
      <PlacePicker
        value={place}
        onChange={(p) => {
          setPlace(p);
          mutation.reset();
        }}
        coordinates={coordinates}
      />
      {place && (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate(new FormData(e.currentTarget));
          }}
        >
          <div className="segmented">
            <button
              type="button"
              aria-pressed={mode === "visit"}
              onClick={() => setMode("visit")}
            >
              曾至 / 将至
            </button>
            <button
              type="button"
              aria-pressed={mode === "wishlist"}
              onClick={() => setMode("wishlist")}
            >
              未至 · 愿望清单
            </button>
          </div>
          {mode === "visit" && (
            <>
              <p className="muted">
                以下时间按本机时区 {deviceTimezone()} 输入，保存后按地点时区{" "}
                {place.timezone} 展示。未来的抵达时间会标为“将至”。
              </p>
              <div className="form-grid">
                <label className="field">
                  抵达时间
                  <input
                    type="datetime-local"
                    name="start"
                    required
                    defaultValue={localDateTime()}
                  />
                </label>
                <label className="field">
                  离开时间（选填）
                  <input type="datetime-local" name="end" />
                </label>
              </div>
              {!tripId && (
                <label className="field">
                  关联旅行
                  <select name="trip" disabled={trips.isPending}>
                    <option value="">独立记录，不关联旅行</option>
                    {trips.data?.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.title}
                      </option>
                    ))}
                  </select>
                  {trips.error && (
                    <span role="status">
                      旅行列表读取失败，仍可保存独立记录。
                    </span>
                  )}
                </label>
              )}
            </>
          )}
          <label className="field">
            备注
            <textarea
              name="note"
              rows={2}
              maxLength={2000}
              placeholder="写下想记住的，或想去的理由。"
            />
          </label>
          {mutation.error && (
            <p role="alert" className="error-message">
              {mutation.error.message}
            </p>
          )}
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending
              ? "保存中…"
              : mode === "visit"
                ? "保存访问记录"
                : "加入愿望清单"}
          </Button>
        </form>
      )}
    </section>
  );
}
