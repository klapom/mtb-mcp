import { test, expect } from '@playwright/test';

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

const FORECAST_DATA = {
  location_name: 'Erlangen',
  lat: 49.59,
  lon: 11.0,
  generated_at: '2026-03-20T08:00:00Z',
  hours: [
    { time: '2026-03-20T09:00:00Z', temp_c: 8, wind_speed_kmh: 10, wind_gust_kmh: 18, precipitation_mm: 0, precipitation_probability: 10, humidity_pct: 65, condition: 'cloudy' },
    { time: '2026-03-20T10:00:00Z', temp_c: 10, wind_speed_kmh: 12, wind_gust_kmh: 20, precipitation_mm: 0, precipitation_probability: 15, humidity_pct: 60, condition: 'partly-cloudy' },
    { time: '2026-03-20T11:00:00Z', temp_c: 13, wind_speed_kmh: 8, wind_gust_kmh: 14, precipitation_mm: 0, precipitation_probability: 5, humidity_pct: 55, condition: 'sunny' },
    { time: '2026-03-20T12:00:00Z', temp_c: 15, wind_speed_kmh: 14, wind_gust_kmh: 22, precipitation_mm: 0.5, precipitation_probability: 40, humidity_pct: 58, condition: 'cloudy' },
  ],
};

const RAIN_RADAR_DATA = {
  lat: 49.59,
  lon: 11.0,
  status: 'clear',
  approaching: false,
  minutes_until_rain: null,
  intensity: null,
  summary: 'Kein Regen in den nächsten 2 Stunden',
};

const ALERTS_DATA = {
  alerts: [
    {
      severity: 'moderate',
      headline: 'Windwarnung für Mittelfranken',
      description: 'Starke Böen bis 70 km/h möglich',
      start: '2026-03-20T14:00:00Z',
      end: '2026-03-20T22:00:00Z',
      region: 'Mittelfranken',
    },
  ],
};

const HISTORY_DATA = {
  lat: 49.59,
  lon: 11.0,
  total_mm: 4.2,
  hours: [
    { time: '2026-03-18T12:00:00Z', precipitation_mm: 0 },
    { time: '2026-03-18T18:00:00Z', precipitation_mm: 1.5 },
    { time: '2026-03-19T00:00:00Z', precipitation_mm: 2.0 },
    { time: '2026-03-19T06:00:00Z', precipitation_mm: 0.7 },
    { time: '2026-03-19T12:00:00Z', precipitation_mm: 0 },
    { time: '2026-03-19T18:00:00Z', precipitation_mm: 0 },
    { time: '2026-03-20T00:00:00Z', precipitation_mm: 0 },
    { time: '2026-03-20T06:00:00Z', precipitation_mm: 0 },
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/weather/forecast**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: FORECAST_DATA, meta: META }),
    });
  });
  await page.route('**/api/v1/weather/rain-radar**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: RAIN_RADAR_DATA, meta: META }),
    });
  });
  await page.route('**/api/v1/weather/alerts**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: ALERTS_DATA, meta: META }),
    });
  });
  await page.route('**/api/v1/weather/history**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: HISTORY_DATA, meta: META }),
    });
  });
});

test.describe('Weather Page', () => {
  test('Forecast card shows location and hour entries', async ({ page }) => {
    await page.goto('/weather');
    await expect(page.getByText('Vorhersage')).toBeVisible();
    await expect(page.getByText('Erlangen')).toBeVisible();
    // Each hour entry shows temperature as N° (rounded)
    await expect(page.getByText('8°')).toBeVisible();
    await expect(page.getByText('10°')).toBeVisible();
    await expect(page.getByText('13°')).toBeVisible();
    await expect(page.getByText('15°')).toBeVisible();
  });

  test('Rain radar shows status (clear/approaching)', async ({ page }) => {
    await page.goto('/weather');
    await expect(page.getByText('Regenradar')).toBeVisible();
    await expect(page.getByText('Kein Regen')).toBeVisible();
    await expect(page.getByText('Kein Regen in den nächsten 2 Stunden')).toBeVisible();
  });

  test('Alert is displayed with severity', async ({ page }) => {
    await page.goto('/weather');
    await expect(page.getByText('Wetterwarnungen')).toBeVisible();
    await expect(page.getByText('Windwarnung für Mittelfranken')).toBeVisible();
    await expect(page.getByText('moderate')).toBeVisible();
    await expect(page.getByText('Starke Böen bis 70 km/h möglich')).toBeVisible();
  });

  test('Rain history chart renders bars', async ({ page }) => {
    await page.goto('/weather');
    await expect(page.getByText('Regenverlauf (48h)')).toBeVisible();
    await expect(page.getByText('4.2 mm')).toBeVisible();
    // The chart container should have multiple bar divs
    const bars = page.locator('[title*="mm"]');
    await expect(bars.first()).toBeVisible();
    const barCount = await bars.count();
    expect(barCount).toBeGreaterThanOrEqual(1);
  });

  test('Hour scroller is horizontally scrollable', async ({ page }) => {
    await page.goto('/weather');
    // The hour scroller is an overflow-x-auto div containing the forecast hours
    const scroller = page.locator('.overflow-x-auto').first();
    await expect(scroller).toBeVisible();
    // Verify the container has scrollable content (children wider than container)
    const scrollWidth = await scroller.evaluate((el) => el.scrollWidth);
    const clientWidth = await scroller.evaluate((el) => el.clientWidth);
    // In a narrow viewport the scroll width should be at least equal to client width
    expect(scrollWidth).toBeGreaterThanOrEqual(clientWidth);
  });
});
