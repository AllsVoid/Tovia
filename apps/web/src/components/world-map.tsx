"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { outlineMapProvider } from "@/lib/map-provider";
import type { MapPlace, PlaceStatus, Scope } from "@/lib/types";
import { highlightedRegions, placeRegion, regionIndex } from "@/lib/regions";

export default function WorldMap({
  places,
  scope,
  status,
  selectedId,
  onSelect,
}: {
  places: MapPlace[];
  scope: Scope;
  status: PlaceStatus | "all";
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const handlers = useRef({ onSelect });
  const [failed, setFailed] = useState(false);
  const [boundaryError, setBoundaryError] = useState(false);
  const [missing, setMissing] = useState(0);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    handlers.current = { onSelect };
  }, [onSelect]);
  useEffect(() => {
    if (!container.current) return;
    let instance: maplibregl.Map;
    try {
      maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
      instance = new maplibregl.Map({
        container: container.current,
        style: outlineMapProvider.style(),
        ...outlineMapProvider.camera("domestic"),
        maxZoom: 15,
        renderWorldCopies: false,
      });
    } catch {
      queueMicrotask(() => setFailed(true));
      return;
    }
    map.current = instance;
    instance.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    instance.on("error", () => setFailed(true));
    instance.once("idle", () => {
      if (container.current) container.current.dataset.ready = "true";
    });
    instance.on("click", (event) => {
      if (!instance.getLayer("places")) return;
      const features = instance.queryRenderedFeatures(event.point, {
        layers: ["places"],
      });
      const id = features[0]?.properties?.place_id;
      if (id) handlers.current.onSelect(String(id));
    });
    const resize = new ResizeObserver(() => instance.resize());
    resize.observe(container.current);
    return () => {
      resize.disconnect();
      instance.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    let cancelled = false;
    const update = () => {
      void highlightedRegions(places, status, selectedId)
        .then(async ({ data, missing }) => {
          if (cancelled) return;
          const source = instance.getSource("visits") as
            GeoJSONSource | undefined;
          await source?.setData(data);
          if (cancelled) return;
          setMissing(missing);
          setBoundaryError(false);
          if (container.current)
            container.current.dataset.regionCount = String(
              data.features.length,
            );
        })
        .catch(() => {
          if (!cancelled) setBoundaryError(true);
        });
    };
    if (instance.getSource("visits")) update();
    else instance.once("load", update);
    return () => {
      cancelled = true;
      instance.off("load", update);
    };
  }, [places, status, selectedId, retry]);
  useEffect(() => {
    map.current?.jumpTo(outlineMapProvider.camera(scope));
  }, [scope]);
  useEffect(() => {
    const instance = map.current;
    const p = places.find((item) => item.id === selectedId);
    if (!instance || !p) return;
    let cancelled = false;
    void regionIndex()
      .then((regions) => placeRegion(p, regions))
      .then((region) => {
        if (!region || cancelled) return;
        instance.fitBounds(region.bbox, {
          padding: 55,
          maxZoom: 10,
          duration: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? 0
            : 500,
        });
      })
      .catch(() => {
        if (!cancelled) setBoundaryError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, places]);
  return (
    <div>
      <div ref={container} className="map-canvas" aria-label="我的旅行地图" />
      {boundaryError && (
        <p role="status" className="muted mt-2">
          行政区边界加载失败，记录已保留。
          <button
            className="text-button"
            onClick={() => setRetry((n) => n + 1)}
          >
            重试边界
          </button>
        </p>
      )}
      {missing > 0 && (
        <p className="muted mt-2">
          {missing} 个已有地点暂未匹配到行政区边界，仍可在列表查看。
        </p>
      )}
      {failed && (
        <p role="status" className="muted mt-2">
          地图暂时不可用。你仍可通过地点列表查看与添加记录。
        </p>
      )}
    </div>
  );
}
