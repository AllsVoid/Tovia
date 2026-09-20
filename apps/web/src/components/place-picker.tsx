"use client";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Place } from "@/lib/api";
import { Button } from "./ui/button";
import { QueryError } from "./query-error";

export function PlacePicker({
  value,
  onChange,
}: {
  value: Place | null;
  onChange: (place: Place | null) => void;
}) {
  const [q, setQ] = useState("");
  const search = useQuery({
    queryKey: ["regions", q.trim()],
    queryFn: () => api.regions(q.trim()),
    enabled: !value && q.trim().length > 0,
  });
  const mutation = useMutation({
    mutationFn: api.regionPlace,
    onSuccess: onChange,
  });
  if (value)
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted p-4">
        <div>
          <strong className="font-medium">{value.canonical_name}</strong>
          <p className="muted">{value.admin1 ?? value.country_code}</p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            mutation.reset();
            onChange(null);
          }}
        >
          更换地点
        </Button>
      </div>
    );
  return (
    <section className="space-y-4" aria-label="选择地点">
      <label className="field">
        城市或行政区
        <input
          value={q}
          maxLength={200}
          onChange={(e) => setQ(e.target.value)}
          placeholder="例如：南京、鼓楼区，或 nanjing"
        />
      </label>
      <p className="muted">
        选择省、市或区县，保存到访后在地图上高亮对应区域。海外目前支持国家或地区。
      </p>
      {q.trim() && search.isPending && (
        <p role="status" className="muted">
          正在搜索…
        </p>
      )}
      {search.error && (
        <QueryError error={search.error} retry={() => void search.refetch()} />
      )}
      <div className="grid gap-2 sm:grid-cols-2">
        {search.data?.map((r) => (
          <button
            type="button"
            key={r.id}
            disabled={mutation.isPending}
            className="rounded-lg border border-border p-3 text-left hover:bg-muted disabled:opacity-50"
            onClick={() => mutation.mutate(r.id)}
          >
            <span>{r.name}</span>
            <p className="muted">{r.path}</p>
          </button>
        ))}
      </div>
      {search.data?.length === 0 && (
        <p className="muted">
          没有匹配的行政区。试试城市全名或所属省份；当前不支持的地区不会要求你填写坐标。
        </p>
      )}
      {search.data?.length === 30 && (
        <p className="muted">显示前 30 个结果，请输入更具体的名称。</p>
      )}
      {mutation.isPending && (
        <p role="status" className="muted">
          正在选择地点…
        </p>
      )}
      {mutation.error && (
        <p role="alert" className="error-message">
          {mutation.error.message}
        </p>
      )}
    </section>
  );
}
