import { test, expect } from '@playwright/test';

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

const TRAILS_ALL = [
  {
    osm_id: 12345,
    name: 'Buckenhofer Trail',
    difficulty: 'S0',
    surface: 'dirt',
    length_m: 2400,
    lat: 49.58,
    lon: 11.02,
    condition: { surface: 'dirt', condition: 'dry', confidence: 'high', rain_48h_mm: 0 },
  },
  {
    osm_id: 23456,
    name: 'Rathsberg Flowtrail',
    difficulty: 'S1',
    surface: 'gravel',
    length_m: 3100,
    lat: 49.57,
    lon: 11.03,
    condition: { surface: 'gravel', condition: 'damp', confidence: 'medium', rain_48h_mm: 3 },
  },
  {
    osm_id: 34567,
    name: 'Kalchreuth Enduro',
    difficulty: 'S2',
    surface: 'rock',
    length_m: 1800,
    lat: 49.60,
    lon: 11.05,
    condition: { surface: 'rock', condition: 'wet', confidence: 'low', rain_48h_mm: 12 },
  },
];

const TRAILS_S1_ONLY = [TRAILS_ALL[1]];

const TRAIL_DETAIL = {
  osm_id: 12345,
  name: 'Buckenhofer Trail',
  difficulty: 'S0',
  surface: 'dirt',
  length_m: 2400,
  lat: 49.58,
  lon: 11.02,
  description: 'Schöner Anfänger-Trail durch den Buckenhofer Wald.',
  elevation_gain_m: 120,
  tags: { 'mtb:scale': '0', sac_scale: 'hiking' },
  condition: { surface: 'dirt', condition: 'dry', confidence: 'high', rain_48h_mm: 0 },
};

test.describe('Trails Page', () => {
  test('Trail list loads and shows 3 cards', async ({ page }) => {
    await page.route('**/api/v1/trails**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: TRAILS_ALL, meta: META }),
      });
    });

    await page.goto('/trails');
    const cards = page.getByTestId('trail-card');
    await expect(cards).toHaveCount(3);
    await expect(page.getByText('Buckenhofer Trail')).toBeVisible();
    await expect(page.getByText('Rathsberg Flowtrail')).toBeVisible();
    await expect(page.getByText('Kalchreuth Enduro')).toBeVisible();
  });

  test('Difficulty filter chips are visible (All, S0, S1, S2, S3)', async ({ page }) => {
    await page.route('**/api/v1/trails**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: TRAILS_ALL, meta: META }),
      });
    });

    await page.goto('/trails');
    // The chips are buttons with these labels
    for (const label of ['All', 'S0', 'S1', 'S2', 'S3']) {
      await expect(page.getByRole('button', { name: label, exact: true })).toBeVisible();
    }
  });

  test('Clicking S1 filter shows only S1 trails', async ({ page }) => {
    let requestCount = 0;
    await page.route('**/api/v1/trails**', async (route) => {
      const url = route.request().url();
      requestCount++;
      // If the URL contains min_difficulty=S1, return only S1 trails
      if (url.includes('min_difficulty=S1')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: TRAILS_S1_ONLY, meta: META }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: TRAILS_ALL, meta: META }),
        });
      }
    });

    await page.goto('/trails');
    await expect(page.getByTestId('trail-card')).toHaveCount(3);

    // Click the S1 filter chip
    await page.getByRole('button', { name: 'S1', exact: true }).click();
    await expect(page.getByTestId('trail-card')).toHaveCount(1);
    await expect(page.getByText('Rathsberg Flowtrail')).toBeVisible();
  });

  test('Trail card shows name + difficulty badge + condition dot', async ({ page }) => {
    await page.route('**/api/v1/trails**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: TRAILS_ALL, meta: META }),
      });
    });

    await page.goto('/trails');
    const firstCard = page.getByTestId('trail-card').first();
    await expect(firstCard).toBeVisible();
    // Card should contain the trail name
    await expect(firstCard.getByText('Buckenhofer Trail')).toBeVisible();
    // Card should contain the difficulty badge
    await expect(firstCard.getByText('S0')).toBeVisible();
    // Card should contain the condition dot
    await expect(firstCard.getByTestId('condition-dot')).toBeVisible();
  });

  test('Clicking trail card navigates to /trails/12345', async ({ page }) => {
    await page.route('**/api/v1/trails**', async (route) => {
      const url = route.request().url();
      // Match the detail endpoint /trails/12345
      if (/\/trails\/12345$/.test(url)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: TRAIL_DETAIL, meta: META }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: TRAILS_ALL, meta: META }),
        });
      }
    });

    await page.goto('/trails');
    await page.getByText('Buckenhofer Trail').click();
    await expect(page).toHaveURL('/trails/12345');
    await expect(page.getByRole('heading', { name: 'Buckenhofer Trail' })).toBeVisible();
  });

  test('Empty state shown when no trails match filter', async ({ page }) => {
    await page.route('**/api/v1/trails**', async (route) => {
      const url = route.request().url();
      if (url.includes('min_difficulty=S3')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: [], meta: META }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: TRAILS_ALL, meta: META }),
        });
      }
    });

    await page.goto('/trails');
    await expect(page.getByTestId('trail-card')).toHaveCount(3);

    // Click S3 filter to get empty results
    await page.getByRole('button', { name: 'S3', exact: true }).click();
    await expect(page.getByText('Keine Trails in der Nähe gefunden')).toBeVisible();
  });
});
