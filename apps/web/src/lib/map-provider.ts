import type { StyleSpecification } from "maplibre-gl";
import type { Scope } from "./types";
export interface MapProvider {
  style(): StyleSpecification;
  camera(scope: Scope): { center: [number, number]; zoom: number };
}
// Published WGS84 administrative geometry, served locally without API keys.
export const outlineMapProvider: MapProvider = {
  camera: (scope) =>
    scope === "domestic"
      ? { center: [104, 35], zoom: 2.8 }
      : { center: [30, 20], zoom: 1.2 },
  style: () => ({
    version: 8,
    sources: {
      countries: {
        type: "geojson",
        data: "/maps/countries.geojson",
        attribution:
          '© <a href="https://www.naturalearthdata.com/">Natural Earth</a>',
      },
      provinces: { type: "geojson", data: "/maps/provinces.geojson" },
      cities: {
        type: "geojson",
        data: "/maps/regions/cities.geojson",
        attribution:
          '© <a href="https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov">AreaCity</a>',
      },
      visits: {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      },
    },
    layers: [
      {
        id: "background",
        type: "background",
        paint: { "background-color": "#eef0e8" },
      },
      {
        id: "land",
        type: "fill",
        source: "countries",
        paint: { "fill-color": "#dbe3d4" },
      },
      {
        id: "borders",
        type: "line",
        source: "countries",
        paint: { "line-color": "#fbfcf7", "line-width": 1 },
      },
      {
        id: "provinces",
        type: "line",
        source: "provinces",
        minzoom: 2,
        paint: { "line-color": "#fbfcf7", "line-width": 0.8 },
      },
      {
        id: "city-borders",
        type: "line",
        source: "cities",
        minzoom: 4,
        paint: {
          "line-color": "#a9b5a1",
          "line-width": 0.6,
          "line-opacity": 0.65,
        },
      },
      {
        id: "places",
        type: "fill",
        source: "visits",
        paint: {
          "fill-color": [
            "match",
            ["get", "status"],
            "visited",
            "#3f6849",
            "upcoming",
            "#a8743c",
            "#a6b2d0",
          ],
          "fill-opacity": ["case", ["get", "selected"], 0.8, 0.6],
        },
      },
      {
        id: "region-outlines",
        type: "line",
        source: "visits",
        paint: {
          "line-color": ["case", ["get", "selected"], "#203d2a", "#64775e"],
          "line-width": ["case", ["get", "selected"], 2.5, 1],
        },
      },
    ],
  }),
};
