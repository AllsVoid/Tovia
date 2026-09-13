"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { outlineMapProvider } from "@/lib/map-provider";
import type { MapPlace, PlaceStatus, Scope } from "@/lib/types";

export default function WorldMap({
  places,
  scope,
  status,
  selectedId,
  onSelect,
  onPick,
}: {
  places: MapPlace[];
  scope: Scope;
  status: PlaceStatus | "all";
  selectedId: string | null;
  onSelect: (id: string) => void;
  onPick: (point: [number, number]) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const handlers = useRef({ onSelect, onPick });
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    handlers.current = { onSelect, onPick };
  }, [onSelect, onPick]);
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
      const id = features[0]?.properties?.id;
      if (id) handlers.current.onSelect(String(id));
      else
        handlers.current.onPick([
          Number(event.lngLat.lng.toFixed(5)),
          Number(event.lngLat.lat.toFixed(5)),
        ]);
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
    const update = () => {
      const source = instance.getSource("visits") as GeoJSONSource | undefined;
      void source
        ?.setData({
          type: "FeatureCollection",
          features: places.map((p) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: [p.longitude, p.latitude] },
            properties: {
              id: p.id,
              visit_count: p.visit_count,
              status:
                status !== "all"
                  ? status
                  : p.visit_count
                    ? "visited"
                    : p.upcoming_count
                      ? "upcoming"
                      : "wishlist",
            },
          })),
        })
        .catch(() => setFailed(true));
    };
    if (instance.isStyleLoaded()) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [places, status]);
  useEffect(() => {
    map.current?.jumpTo(outlineMapProvider.camera(scope));
  }, [scope]);
  useEffect(() => {
    const instance = map.current;
    const p = places.find((item) => item.id === selectedId);
    if (!instance || !p) return;
    instance.easeTo({
      center: [p.longitude, p.latitude],
      zoom: Math.max(instance.getZoom(), 4),
      duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? 0
        : 500,
    });
    const text = document.createElement("div");
    text.textContent = p.name;
    const popup = new maplibregl.Popup({ closeButton: false, offset: 12 })
      .setLngLat([p.longitude, p.latitude])
      .setDOMContent(text)
      .addTo(instance);
    return () => {
      popup.remove();
    };
  }, [selectedId, places]);
  return (
    <div>
      <div ref={container} className="map-canvas" aria-label="我的旅行地图" />
      {failed && (
        <p role="status" className="muted mt-2">
          地图暂时不可用。你仍可通过地点列表查看与添加记录。
        </p>
      )}
    </div>
  );
}
