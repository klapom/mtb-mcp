'use client';

import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Trail } from '@/lib/types';

const SCALE_COLORS: Record<string, string> = {
  S0: '#22c55e',
  S1: '#84cc16',
  S2: '#eab308',
  S3: '#f97316',
  S4: '#ef4444',
  S5: '#dc2626',
};

interface TourRouteMapProps {
  tourStart: [number, number];
  tourName: string;
  trailFragments: Trail[];
  corridorKm: number;
}

export function TourRouteMap({ tourStart, tourName, trailFragments, corridorKm }: TourRouteMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current) return;
    if (mapInstance.current) {
      mapInstance.current.remove();
      mapInstance.current = null;
    }

    const map = L.map(mapRef.current, { zoomControl: true, attributionControl: false });
    mapInstance.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap',
    }).addTo(map);

    const bounds = L.latLngBounds([]);

    // Tour start marker
    const startMarker = L.circleMarker(tourStart, {
      radius: 10,
      color: '#0f9b58',
      fillColor: '#0f9b58',
      fillOpacity: 1,
      weight: 3,
    }).addTo(map);
    startMarker.bindPopup(`<b>${tourName}</b><br/>Start`);
    bounds.extend(tourStart);

    // Corridor circle (visual hint)
    L.circle(tourStart, {
      radius: corridorKm * 1000,
      color: '#0f9b58',
      fillColor: '#0f9b58',
      fillOpacity: 0.05,
      weight: 1,
      dashArray: '4 4',
    }).addTo(map);

    // Trail fragments as colored polylines
    for (const trail of trailFragments) {
      if (!trail.geometry || trail.geometry.length < 2) continue;

      const latlngs: L.LatLngExpression[] = trail.geometry.map((p) => [p.lat, p.lon]);
      const scale = trail.mtb_scale || trail.difficulty || 'S0';
      const color = SCALE_COLORS[scale] ?? '#888888';

      const polyline = L.polyline(latlngs, {
        color,
        weight: 4,
        opacity: 0.85,
      }).addTo(map);

      const surfaceLabels: Record<string, string> = {
        dirt: 'Erde', gravel: 'Schotter', rock: 'Fels', roots: 'Wurzeln',
      };
      const surfLabel = surfaceLabels[trail.surface] ?? trail.surface;
      const lengthKm = (trail.length_m / 1000).toFixed(1);

      polyline.bindPopup(
        `<b>${trail.name || 'Trail'}</b><br/>${scale} · ${lengthKm} km · ${surfLabel}`,
      );

      for (const pt of latlngs) {
        bounds.extend(pt);
      }
    }

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [30, 30] });
    } else {
      map.setView(tourStart, 13);
    }

    return () => {
      map.remove();
      mapInstance.current = null;
    };
  }, [tourStart, tourName, trailFragments, corridorKm]);

  return <div ref={mapRef} className="h-[300px] rounded-xl overflow-hidden border border-border-card" />;
}
