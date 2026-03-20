import type { WeatherCurrent } from "@/lib/types";

const conditionIcons: Record<string, string> = {
  sunny: "☀️",
  clear: "☀️",
  "partly-cloudy": "⛅",
  cloudy: "☁️",
  rain: "🌧️",
  snow: "🌨️",
  thunderstorm: "⛈️",
  fog: "🌫️",
};

export function WeatherStrip({ weather }: { weather: WeatherCurrent }) {
  const icon = conditionIcons[weather.condition] ?? "🌤️";
  return (
    <div className="flex items-center gap-4" data-testid="weather-strip">
      <span className="text-2xl">{icon}</span>
      <div>
        <span className="text-xl font-bold" data-testid="weather-temp">
          {Math.round(weather.temp_c)}°C
        </span>
        <div className="text-xs text-text-secondary">
          Wind {weather.wind_speed_kmh} km/h · {weather.humidity_pct}%
        </div>
      </div>
      {weather.precipitation_mm > 0 && (
        <span className="text-xs text-accent-blue">
          {weather.precipitation_mm} mm
        </span>
      )}
    </div>
  );
}
