"use client";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Place, type PlaceInput } from "@/lib/api";
import { Button } from "./ui/button";
import { QueryError } from "./query-error";

export function PlacePicker({
  value,
  onChange,
  coordinates,
}: {
  value: Place | null;
  onChange: (place: Place | null) => void;
  coordinates?: [number, number];
}) {
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(Boolean(coordinates));
  const search = useQuery({
    queryKey: ["places", q],
    queryFn: () => api.places(q),
    enabled: !value && !creating,
  });
  const mutation = useMutation({
    mutationFn: (input: PlaceInput) => api.createPlace(input),
    onSuccess: (place) => {
      onChange(place);
      setCreating(false);
    },
  });
  if (value)
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted p-4">
        <div>
          <strong className="font-medium">{value.canonical_name}</strong>
          <p className="muted">
            {value.country_code ?? "地区未设置"} · {value.timezone}
          </p>
        </div>
        <Button type="button" variant="outline" onClick={() => onChange(null)}>
          更换地点
        </Button>
      </div>
    );
  return (
    <section className="space-y-4" aria-label="选择地点">
      <div className="segmented">
        <button
          type="button"
          aria-pressed={!creating}
          onClick={() => setCreating(false)}
        >
          搜索已有地点
        </button>
        <button
          type="button"
          aria-pressed={creating}
          onClick={() => setCreating(true)}
        >
          手工添加地点
        </button>
      </div>
      {!creating ? (
        <>
          <label className="field">
            地点名称
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="搜索已保存的城市或地点"
            />
          </label>
          {search.isPending && (
            <p role="status" className="muted">
              正在搜索…
            </p>
          )}
          {search.isError && (
            <QueryError
              error={search.error}
              retry={() => void search.refetch()}
            />
          )}
          <div className="grid gap-2 sm:grid-cols-2">
            {search.data?.map((p) => (
              <button
                type="button"
                key={p.id}
                className="rounded-lg border border-border p-3 text-left hover:bg-muted"
                onClick={() => onChange(p)}
              >
                <span>{p.canonical_name}</span>
                <p className="muted">
                  {p.country_code ?? "地区未设置"} · {p.timezone}
                </p>
              </button>
            ))}
          </div>
          {search.data?.length === 0 && (
            <p className="muted">还没有匹配的地点，可以手工添加。</p>
          )}
          {search.data?.length === 20 && (
            <p className="muted">仅显示前 20 个结果，请输入更具体的名称。</p>
          )}
        </>
      ) : (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            mutation.mutate({
              canonical_name: String(form.get("name")).trim(),
              country_code: String(form.get("country")).toUpperCase(),
              timezone: String(form.get("timezone")).trim(),
              latitude: Number(form.get("latitude")),
              longitude: Number(form.get("longitude")),
              city: String(form.get("city")).trim() || undefined,
            });
          }}
        >
          <div className="form-grid">
            <label className="field">
              地点名称
              <input
                name="name"
                required
                maxLength={300}
                defaultValue={q}
                placeholder="例如：大理古城"
              />
            </label>
            <label className="field">
              国家或地区代码
              <input
                name="country"
                required
                pattern="[A-Za-z]{2}"
                maxLength={2}
                defaultValue="CN"
                placeholder="CN / JP / FR"
              />
            </label>
            <label className="field">
              城市（选填）
              <input name="city" maxLength={200} placeholder="大理" />
            </label>
            <label className="field">
              地点时区
              <input
                name="timezone"
                required
                defaultValue="Asia/Shanghai"
                placeholder="Asia/Tokyo"
              />
            </label>
            <label className="field">
              经度
              <input
                name="longitude"
                type="number"
                required
                step="any"
                min={-180}
                max={180}
                defaultValue={coordinates?.[0]}
                placeholder="100.1653"
              />
            </label>
            <label className="field">
              纬度
              <input
                name="latitude"
                type="number"
                required
                step="any"
                min={-90}
                max={90}
                defaultValue={coordinates?.[1]}
                placeholder="25.6944"
              />
            </label>
          </div>
          <p className="muted">
            坐标使用 WGS84。添加海外地点时，请同时修改国家/地区代码和地点时区。
          </p>
          {mutation.error && (
            <p role="alert" className="error-message">
              {mutation.error.message}
            </p>
          )}
          <Button disabled={mutation.isPending} type="submit">
            {mutation.isPending ? "保存中…" : "保存并选择地点"}
          </Button>
        </form>
      )}
    </section>
  );
}
