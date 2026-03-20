import { test, expect } from '@playwright/test';

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

const TOURS_SEARCH = [
  {
    id: 'tour1',
    source: 'komoot',
    name: 'Frankenjura Rundtour',
    distance_km: 42.5,
    elevation_up_m: 850,
    elevation_down_m: 850,
    duration_minutes: 195,
    difficulty: 'S1',
    sport: 'mtb',
    image_url: null,
  },
  {
    id: 'tour2',
    source: 'gps-tour',
    name: 'Nürnberger Land Trail',
    distance_km: 28.3,
    elevation_up_m: 520,
    elevation_down_m: 520,
    duration_minutes: 140,
    difficulty: 'S2',
    sport: 'mtb',
    image_url: null,
  },
];

const TOUR_DETAIL = {
  id: 'tour1',
  source: 'komoot',
  name: 'Frankenjura Rundtour',
  distance_km: 42.5,
  elevation_up_m: 850,
  elevation_down_m: 850,
  duration_minutes: 195,
  difficulty: 'S1',
  sport: 'mtb',
  image_url: null,
  description: 'Eine traumhafte MTB-Runde durch den Frankenjura.',
  start_lat: 49.59,
  start_lon: 11.0,
  gpx_available: true,
  segments: [
    { name: 'Auffahrt Walberla', distance_km: 5.2, difficulty: 'S0' },
    { name: 'Trailabfahrt Nord', distance_km: 3.1, difficulty: 'S1' },
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/tours/search**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: TOURS_SEARCH, meta: META }),
    });
  });
  await page.route('**/api/v1/tours/komoot/tour1', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: TOUR_DETAIL, meta: META }),
    });
  });
});

test.describe('Tours Page', () => {
  test('Tour search shows results', async ({ page }) => {
    await page.goto('/tours');
    const cards = page.getByTestId('tour-card');
    await expect(cards).toHaveCount(2);
    await expect(page.getByText('Frankenjura Rundtour')).toBeVisible();
    await expect(page.getByText('Nürnberger Land Trail')).toBeVisible();
  });

  test('Tour card shows distance, elevation, duration', async ({ page }) => {
    await page.goto('/tours');
    const firstCard = page.getByTestId('tour-card').first();
    await expect(firstCard.getByTestId('tour-distance')).toHaveText('42.5 km');
    await expect(firstCard.getByTestId('tour-elevation')).toContainText('850 m');
    await expect(firstCard.getByTestId('tour-duration')).toHaveText('3h 15m');
  });

  test('Source badge shows "Komoot" or "GPS-Tour"', async ({ page }) => {
    await page.goto('/tours');
    const firstCard = page.getByTestId('tour-card').first();
    await expect(firstCard.getByText('Komoot')).toBeVisible();

    const secondCard = page.getByTestId('tour-card').nth(1);
    await expect(secondCard.getByText('GPS-Tour')).toBeVisible();
  });

  test('Tour detail page shows stats', async ({ page }) => {
    await page.goto('/tours');
    await page.getByText('Frankenjura Rundtour').click();
    await expect(page).toHaveURL('/tours/komoot/tour1');
    await expect(page.getByRole('heading', { name: 'Frankenjura Rundtour' })).toBeVisible();
    await expect(page.getByText('42.5 km')).toBeVisible();
    await expect(page.getByText('Beschreibung')).toBeVisible();
    await expect(page.getByText('Eine traumhafte MTB-Runde durch den Frankenjura.')).toBeVisible();
  });

  test('GPX download button is visible', async ({ page }) => {
    await page.goto('/tours/komoot/tour1');
    await expect(page.getByText('GPX Herunterladen')).toBeVisible();
    // Verify it's a download link
    const gpxLink = page.locator('a[download]', { hasText: 'GPX Herunterladen' });
    await expect(gpxLink).toBeVisible();
  });
});
