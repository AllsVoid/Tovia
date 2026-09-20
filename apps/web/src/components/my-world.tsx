"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  api,
  type MapPlace,
  type Place,
  type PlaceStatus,
  type Scope,
} from "@/lib/api";
import { formatInstant } from "@/lib/dates";
import { refreshTravel } from "@/lib/queries";
import { Button } from "./ui/button";
import { QueryError } from "./query-error";
import { RecordPlace } from "./record-place";

const WorldMap = dynamic(() => import("./world-map"), {
  ssr: false,
  loading: () => (
    <div className="map-canvas grid place-items-center muted" role="status">
      正在准备地图…
    </div>
  ),
});
const scopeLabels: [Scope, string][] = [
  ["domestic", "国内"],
  ["international", "海外"],
  ["all", "全部"],
];
const statusLabels: [PlaceStatus | "all", string][] = [
  ["all", "全部状态"],
  ["visited", "● 曾至"],
  ["upcoming", "● 将至"],
  ["wishlist", "○ 未至"],
];
function asPlace(p: MapPlace): Place {
  return {
    ...p,
    canonical_name: p.name,
    metadata: p.region_id ? { region_id: p.region_id } : undefined,
  };
}
function StatusText({ place: p }: { place: MapPlace }) {
  return (
    <span className="muted">
      {[
        p.visit_count ? `曾至 ${p.visit_count} 次` : "",
        p.upcoming_count ? `将至 ${p.upcoming_count} 次` : "",
        p.wishlist ? "未至收藏" : "",
      ]
        .filter(Boolean)
        .join(" · ")}
    </span>
  );
}
export function MyWorld() {
  const params = useSearchParams();
  const [scope, setScope] = useState<Scope>(
    params.get("place") ? "all" : "domestic",
  );
  const [status, setStatus] = useState<PlaceStatus | "all">("all");
  const [selected, setSelected] = useState<string | null>(params.get("place"));
  const [record, setRecord] = useState<{
    place?: Place;
  } | null>(null);
  const client = useQueryClient();
  const summary = useQuery({
    queryKey: ["map", "summary", scope],
    queryFn: () => api.mapSummary(scope),
  });
  const query = useInfiniteQuery({
    queryKey: ["map", "places", scope, status],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => api.mapPlaces(scope, status, pageParam),
    getNextPageParam: (last) =>
      last.offset + last.places.length < last.total
        ? last.offset + last.places.length
        : undefined,
  });
  const places = useMemo(
    () => query.data?.pages.flatMap((p) => p.places) ?? [],
    [query.data],
  );
  const detail = useQuery({
    queryKey: ["map", "detail", selected],
    queryFn: () => api.mapDetail(selected!),
    enabled: Boolean(selected),
  });
  const mapPlaces = useMemo(() => {
    const focus = detail.data?.place;
    return focus &&
      selected === focus.id &&
      !places.some((p) => p.id === focus.id)
      ? [...places, focus]
      : places;
  }, [places, detail.data, selected]);
  const remove = useMutation({
    mutationFn: ({ kind, id }: { kind: "wish" | "visit"; id: string }) =>
      kind === "wish" ? api.removeWishlist(id) : api.deleteVisit(id),
    onSuccess: async () => {
      setSelected(null);
      await refreshTravel(client);
    },
  });
  return (
    <section className="space-y-6">
      <div className="page-heading">
        <div>
          <p className="eyebrow">MY WORLD</p>
          <h1>凡我所至，皆有所记。</h1>
          <p className="muted mt-2">用每一次出发，慢慢绘出自己的世界。</p>
        </div>
        <Button onClick={() => setRecord({})}>＋ 记录地点</Button>
      </div>
      {record && (
        <RecordPlace
          key={JSON.stringify(record)}
          initialPlace={record.place}
          onDone={(place) => {
            setRecord(null);
            setSelected(place.id);
            setScope("all");
            setStatus("all");
          }}
          onCancel={() => setRecord(null)}
        />
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="segmented" aria-label="地图范围">
          {scopeLabels.map(([value, label]) => (
            <button
              key={value}
              aria-pressed={scope === value}
              onClick={() => {
                setScope(value);
                setSelected(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="segmented" aria-label="地点状态">
          {statusLabels.map(([value, label]) => (
            <button
              key={value}
              aria-pressed={status === value}
              onClick={() => {
                setStatus(value);
                setSelected(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {summary.data && (
        <div className="flex flex-wrap gap-7 text-sm" aria-label="地图统计">
          <span>
            <strong className="text-2xl font-normal">
              {summary.data.visited_places}
            </strong>{" "}
            个曾至地点
          </span>
          <span>
            <strong className="text-2xl font-normal">
              {summary.data.upcoming_places}
            </strong>{" "}
            个将至地点
          </span>
          <span>
            <strong className="text-2xl font-normal">
              {summary.data.wishlist_places}
            </strong>{" "}
            个愿望地点
          </span>
          <span className="muted self-end">
            累计 {summary.data.visit_count} 次访问
          </span>
        </div>
      )}
      {summary.error && (
        <QueryError
          error={summary.error}
          retry={() => void summary.refetch()}
        />
      )}
      <div className="map-layout">
        <div>
          <WorldMap
            places={mapPlaces}
            scope={scope}
            status={status}
            selectedId={selected}
            onSelect={setSelected}
          />
          <p className="muted mt-2">
            已记录的行政区以颜色高亮：绿色曾至、赭色将至、淡紫色未至。点击高亮区域查看记录。
          </p>
        </div>
        <aside aria-label="地点列表">
          {query.isPending && (
            <p role="status" className="muted">
              正在读取地点…
            </p>
          )}
          {query.error && (
            <QueryError
              error={query.error}
              retry={() => void query.refetch()}
            />
          )}
          {query.isSuccess && places.length === 0 && (
            <div className="empty-state">
              这里还没有地点。
              <br />
              添加一次访问，或收藏一个愿望目的地。
            </div>
          )}
          <div className="place-list">
            {places.map((p) => (
              <button
                key={p.id}
                aria-pressed={p.id === selected}
                onClick={() => setSelected(p.id)}
              >
                <span className="block font-medium">{p.name}</span>
                <StatusText place={p} />
              </button>
            ))}
          </div>
          {query.data && (
            <p className="muted my-3">
              已显示 {places.length} / {query.data.pages[0].total} 个地点
            </p>
          )}
          {query.hasNextPage && (
            <Button
              variant="outline"
              disabled={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}
            >
              加载更多地点
            </Button>
          )}
        </aside>
      </div>
      {scope === "all" && Boolean(summary.data?.unknown_country_places) && (
        <p className="muted">
          包含 {summary.data?.unknown_country_places}{" "}
          个尚未设置国家/地区的地点，它们仅在“全部”中显示。
        </p>
      )}
      {selected && detail.isPending && <p role="status">正在读取地点详情…</p>}
      {selected && detail.error && (
        <QueryError error={detail.error} retry={() => void detail.refetch()} />
      )}
      {selected && detail.data && (
        <section className="panel" aria-label="地点详情">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl">{detail.data.place.name}</h2>
              <StatusText place={detail.data.place} />
              <p className="muted">{detail.data.place.timezone}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() =>
                  setRecord({ place: asPlace(detail.data!.place) })
                }
              >
                添加访问
              </Button>
              {detail.data.place.wishlist && (
                <Button
                  variant="outline"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate({ kind: "wish", id: selected })}
                >
                  移出愿望清单
                </Button>
              )}
            </div>
          </div>
          {detail.data.wishlist_note && (
            <p className="mt-4 whitespace-pre-wrap">
              {detail.data.wishlist_note}
            </p>
          )}
          {detail.data.visits.map((v) => (
            <div className="travel-row" key={v.id}>
              <div>
                <p>
                  {formatInstant(v.visited_at, detail.data!.place.timezone)}
                </p>
                {v.ended_at && (
                  <p className="muted">
                    至 {formatInstant(v.ended_at, detail.data!.place.timezone)}
                  </p>
                )}
                {v.note && (
                  <p className="muted whitespace-pre-wrap">{v.note}</p>
                )}
                {v.trip_id && (
                  <Link
                    href={`/trips/${v.trip_id}`}
                    className="text-sm underline underline-offset-4"
                  >
                    查看关联旅行 →
                  </Link>
                )}
              </div>
              <Button
                variant="outline"
                disabled={remove.isPending}
                onClick={() => {
                  if (
                    window.confirm("删除这次访问记录？地点和其他访问会保留。")
                  )
                    remove.mutate({ kind: "visit", id: v.id });
                }}
              >
                删除访问
              </Button>
            </div>
          ))}
          <p className="muted mt-3">
            显示最近 {detail.data.visits.length} / {detail.data.visits_total}{" "}
            条访问记录。
          </p>
        </section>
      )}
      {remove.error && (
        <p role="alert" className="error-message">
          {remove.error.message}
        </p>
      )}
      <div className="flex justify-end">
        <Button asChild variant="outline">
          <Link href="/trips">我的旅行</Link>
        </Button>
      </div>
    </section>
  );
}
