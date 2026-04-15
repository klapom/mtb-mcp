'use client';

import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface TrailMapProps {
  geometry: { lat: number; lon: number; ele: number | null }[];
}

export function TrailMap({ geometry }: TrailMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || geometry.length === 0) return;
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

    const latlngs: L.LatLngExpression[] = geometry.map((p) => [p.lat, p.lon]);
    const polyline = L.polyline(latlngs, { color: '#0f9b58', weight: 4, opacity: 0.9 }).addTo(map);

    // Start/end markers
    if (latlngs.length > 0) {
      L.circleMarker(latlngs[0] as L.LatLngExpression, {
        radius: 6,
        color: '#0f9b58',
        fillColor: '#0f9b58',
        fillOpacity: 1,
      }).addTo(map);
      L.circleMarker(latlngs[latlngs.length - 1] as L.LatLngExpression, {
        radius: 6,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 1,
      }).addTo(map);
    }

    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });

    return () => {
      map.remove();
      mapInstance.current = null;
    };
  }, [geometry]);

  return <div ref={mapRef} className="h-[250px] rounded-xl overflow-hidden border border-border-card" />;
}
