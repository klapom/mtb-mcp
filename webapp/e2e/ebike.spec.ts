import { test, expect } from '@playwright/test';

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

const RANGE_CHECK_RESULT = {
  feasible: true,
  verdict: 'Die Tour ist mit dem aktuellen Ladestand gut machbar.',
  estimated_range_km: 65,
  route_distance_km: 45,
  elevation_gain_m: 1200,
  battery_at_finish_pct: 32,
  modes: [
    { mode: 'Eco', range_km: 90, battery_pct: 50 },
    { mode: 'Trail', range_km: 65, battery_pct: 32 },
    { mode: 'Boost', range_km: 40, battery_pct: 0 },
  ],
};

test.describe('eBike Page', () => {
  test('Range check form is visible with all inputs', async ({ page }) => {
    await page.goto('/ebike');
    await expect(page.getByRole('heading', { name: 'eBike Range Check' })).toBeVisible();
    // All form labels
    await expect(page.getByText('Akku (Wh)')).toBeVisible();
    await expect(page.getByText(/Ladestand/)).toBeVisible();
    await expect(page.getByText('Distanz (km)')).toBeVisible();
    await expect(page.getByText('Höhenmeter (m)')).toBeVisible();
    await expect(page.getByText('Fahrergewicht (kg)')).toBeVisible();
    // Submit button
    await expect(page.getByRole('button', { name: 'Berechnen' })).toBeVisible();
  });

  test('Submitting calculation shows result with verdict', async ({ page }) => {
    await page.route('**/api/v1/ebike/range-check', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: RANGE_CHECK_RESULT, meta: META }),
      });
    });

    await page.goto('/ebike');
    // Fill in the required fields
    await page.getByPlaceholder('z.B. 45').fill('45');
    await page.getByPlaceholder('z.B. 1200').fill('1200');
    // Click calculate
    await page.getByRole('button', { name: 'Berechnen' }).click();

    // Wait for result
    await expect(page.getByText('Ergebnis')).toBeVisible();
    await expect(page.getByText('Machbar')).toBeVisible();
    await expect(page.getByText('Die Tour ist mit dem aktuellen Ladestand gut machbar.')).toBeVisible();
    // Distance stats
    await expect(page.getByText('65 km')).toBeVisible();
    await expect(page.getByText('45 km')).toBeVisible();
    await expect(page.getByText('1200 m')).toBeVisible();
  });

  test('Battery info displays correctly', async ({ page }) => {
    await page.route('**/api/v1/ebike/range-check', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: RANGE_CHECK_RESULT, meta: META }),
      });
    });

    await page.goto('/ebike');
    await page.getByPlaceholder('z.B. 45').fill('45');
    await page.getByPlaceholder('z.B. 1200').fill('1200');
    await page.getByRole('button', { name: 'Berechnen' }).click();

    // Battery at finish
    await expect(page.getByText('Akku am Ziel')).toBeVisible();
    await expect(page.getByText('32%')).toBeVisible();

    // Modes comparison table
    await expect(page.getByText('Modi-Vergleich')).toBeVisible();
    await expect(page.getByText('Eco')).toBeVisible();
    await expect(page.getByText('Trail')).toBeVisible();
    await expect(page.getByText('Boost')).toBeVisible();
  });
});
