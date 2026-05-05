// This project was developed with assistance from AI tools.

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Feature, FeatureCollection, Point, LineString } from "geojson";
import type { TopologyData, AssetRiskScore, FaultEvent, DispatchAssignment } from "../types/events";

interface GridMapProps {
  assets: TopologyData["assets"];
  segments: TopologyData["segments"];
  cameras: TopologyData["cameras"];
  riskScores: Map<string, AssetRiskScore>;
  faults: FaultEvent[];
  dispatches: DispatchAssignment[];
  scenarioActive: boolean;
}

function riskColor(score: number): string {
  if (score >= 0.85) return "#A30000";
  if (score >= 0.65) return "#EE0000";
  if (score >= 0.40) return "#F0AB00";
  return "#3E8635";
}

function segmentColor(status: string): string {
  if (status === "faulted") return "#A30000";
  if (status === "de-energized") return "#6A6E73";
  return "#3E8635";
}

function fc(features: Feature[]): FeatureCollection {
  return { type: "FeatureCollection", features };
}

const EMPTY_FC = fc([]);

const SOURCE_IDS = {
  assets: "grid-assets",
  segments: "grid-segments",
  cameras: "grid-cameras",
  faults: "grid-faults",
  routes: "grid-routes",
  weather: "grid-weather",
} as const;



export function GridMap({ assets, segments, cameras, riskScores, faults, dispatches, scenarioActive }: GridMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const fittedRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [-79.46, 36.09],
      zoom: 12,
    });

    map.on("load", () => {
      // Weather overlay added dynamically when forecast data arrives

      map.addSource(SOURCE_IDS.segments, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "segments-layer",
        type: "line",
        source: SOURCE_IDS.segments,
        paint: {
          "line-color": ["get", "color"],
          "line-width": 3,
          "line-opacity": 0.8,
        },
      });

      map.addSource(SOURCE_IDS.assets, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "assets-layer",
        type: "circle",
        source: SOURCE_IDS.assets,
        paint: {
          "circle-radius": 6,
          "circle-color": ["get", "color"],
          "circle-stroke-width": 1,
          "circle-stroke-color": "#ffffff",
        },
      });

      const diamondSize = 16;
      const canvas = document.createElement("canvas");
      canvas.width = diamondSize;
      canvas.height = diamondSize;
      const ctx = canvas.getContext("2d")!;
      const half = diamondSize / 2;
      ctx.beginPath();
      ctx.moveTo(half, 1);
      ctx.lineTo(diamondSize - 1, half);
      ctx.lineTo(half, diamondSize - 1);
      ctx.lineTo(1, half);
      ctx.closePath();
      ctx.fillStyle = "#0066CC";
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      map.addImage("diamond", { width: diamondSize, height: diamondSize, data: new Uint8Array(ctx.getImageData(0, 0, diamondSize, diamondSize).data) });

      map.addSource(SOURCE_IDS.cameras, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "cameras-layer",
        type: "symbol",
        source: SOURCE_IDS.cameras,
        layout: {
          "icon-image": "diamond",
          "icon-size": 1,
          "icon-allow-overlap": true,
        },
      });

      map.addSource(SOURCE_IDS.routes, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "routes-layer",
        type: "line",
        source: SOURCE_IDS.routes,
        paint: {
          "line-color": "#6753AC",
          "line-width": 2,
          "line-dasharray": [4, 3],
        },
      });

      map.addSource(SOURCE_IDS.faults, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "faults-layer",
        type: "circle",
        source: SOURCE_IDS.faults,
        paint: {
          "circle-radius": 12,
          "circle-color": "#A30000",
          "circle-opacity": 0.6,
          "circle-stroke-width": 2,
          "circle-stroke-color": "#A30000",
        },
      });

      setMapReady(true);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !mapReady) return;
    const map = mapRef.current;

    const assetLookup = new Map(assets.map((a) => [a.id, a]));

    if (assets.length > 0 && !fittedRef.current) {
      fittedRef.current = true;
      const lons = assets.map((a) => a.lon);
      const lats = assets.map((a) => a.lat);
      map.fitBounds(
        [[Math.min(...lons) - 0.01, Math.min(...lats) - 0.005],
         [Math.max(...lons) + 0.01, Math.max(...lats) + 0.005]],
        { padding: 40, maxZoom: 14 }
      );
    }

    const faultedAssets = new Set(faults.flatMap((f) => f.affected_asset_ids ?? []));
    const assetFeatures: Feature<Point>[] = assets.map((a) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [a.lon, a.lat] },
      properties: { id: a.id, color: faultedAssets.has(a.id) ? "#A30000" : riskColor(riskScores.get(a.id)?.composite_score ?? 0) },
    }));
    (map.getSource(SOURCE_IDS.assets) as maplibregl.GeoJSONSource)?.setData(fc(assetFeatures));

    const segmentFeatures = segments.reduce<Feature<LineString>[]>((acc, s) => {
      const from = assetLookup.get(s.from_asset_id);
      const to = assetLookup.get(s.to_asset_id);
      if (from && to) {
        acc.push({
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: [[from.lon, from.lat], [to.lon, to.lat]],
          },
          properties: { id: s.id, color: segmentColor(s.status) },
        });
      }
      return acc;
    }, []);
    (map.getSource(SOURCE_IDS.segments) as maplibregl.GeoJSONSource)?.setData(fc(segmentFeatures));

    const cameraFeatures: Feature<Point>[] = cameras.map((c) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [c.lon, c.lat] },
      properties: { id: c.id },
    }));
    (map.getSource(SOURCE_IDS.cameras) as maplibregl.GeoJSONSource)?.setData(fc(cameraFeatures));

    const faultFeatures: Feature<Point>[] = faults.map((f) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [f.lon, f.lat] },
      properties: { id: f.fault_id },
    }));
    (map.getSource(SOURCE_IDS.faults) as maplibregl.GeoJSONSource)?.setData(fc(faultFeatures));

    const routeFeatures: Feature<LineString>[] = dispatches
      .filter((d) => d.route_polyline?.length >= 2)
      .map((d) => ({
        type: "Feature" as const,
        geometry: {
          type: "LineString" as const,
          coordinates: d.route_polyline.map(([lat, lon]) => [lon, lat]),
        },
        properties: { crew_id: d.crew_id },
      }));
    (map.getSource(SOURCE_IDS.routes) as maplibregl.GeoJSONSource)?.setData(fc(routeFeatures));

    if (scenarioActive) {
      const overlayUrl = "/api/weather/overlay.png?t=" + Date.now();
      fetch(overlayUrl).then(resp => {
        if (!resp.ok) return;
        const bounds = resp.headers.get("X-Overlay-Bounds");
        if (!bounds) return;
        const [latMin, latMax, lonMin, lonMax] = bounds.split(",").map(Number);
        const coords: [[number, number], [number, number], [number, number], [number, number]] = [
          [lonMin, latMax],
          [lonMax, latMax],
          [lonMax, latMin],
          [lonMin, latMin],
        ];
        if (map.getSource("weather-raster")) {
          (map.getSource("weather-raster") as maplibregl.ImageSource).updateImage({ url: overlayUrl, coordinates: coords });
        } else {
          map.addSource("weather-raster", { type: "image", url: overlayUrl, coordinates: coords });
          map.addLayer({ id: "weather-raster-layer", type: "raster", source: "weather-raster", paint: { "raster-opacity": 0.7 } }, "segments-layer");
        }
      }).catch(() => {});
    } else if (map.getLayer("weather-raster-layer")) {
      map.removeLayer("weather-raster-layer");
      map.removeSource("weather-raster");
    }
  }, [assets, segments, cameras, riskScores, faults, dispatches, mapReady, scenarioActive]);

  return <div ref={containerRef} className="grid-map" />;
}
