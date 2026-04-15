'use client';

interface ElevationProfileProps {
  geometry: { lat: number; lon: number; ele: number | null }[];
}

function haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function ElevationProfile({ geometry }: ElevationProfileProps) {
  // Filter to points with elevation data
  const pointsWithEle = geometry.filter((p) => p.ele != null);
  if (pointsWithEle.length < 2) return null;

  // Build cumulative distance + elevation arrays
  const distances: number[] = [0];
  const elevations: number[] = [pointsWithEle[0].ele!];

  for (let i = 1; i < pointsWithEle.length; i++) {
    const prev = pointsWithEle[i - 1];
    const curr = pointsWithEle[i];
    const d = haversineM(prev.lat, prev.lon, curr.lat, curr.lon);
    distances.push(distances[i - 1] + d);
    elevations.push(curr.ele!);
  }

  const totalDistM = distances[distances.length - 1];
  if (totalDistM === 0) return null;

  const minEle = Math.min(...elevations);
  const maxEle = Math.max(...elevations);
  const eleRange = maxEle - minEle || 1;

  // SVG dimensions
  const width = 400;
  const height = 120;
  const padLeft = 0;
  const padRight = 0;
  const padTop = 8;
  const padBottom = 4;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  // Build path
  const points = distances.map((d, i) => {
    const x = padLeft + (d / totalDistM) * plotW;
    const y = padTop + plotH - ((elevations[i] - minEle) / eleRange) * plotH;
    return { x, y };
  });

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  const areaPath = `${linePath} L${points[points.length - 1].x},${padTop + plotH} L${points[0].x},${padTop + plotH} Z`;

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[120px]" preserveAspectRatio="none">
        <defs>
          <linearGradient id="eleFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f9b58" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#0f9b58" stopOpacity="0.05" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#eleFill)" />
        <path d={linePath} fill="none" stroke="#0f9b58" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="flex justify-between text-[11px] text-text-muted mt-1 px-1">
        <span>Min {Math.round(minEle)} m</span>
        <span>{(totalDistM / 1000).toFixed(1)} km</span>
        <span>Max {Math.round(maxEle)} m</span>
      </div>
    </div>
  );
}
