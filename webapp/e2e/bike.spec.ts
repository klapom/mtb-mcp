import { test, expect } from '@playwright/test';

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

const BIKES = [
  {
    id: 'bike1',
    name: 'Spectral 125',
    type: 'Trail',
    total_km: 3200,
    component_count: 5,
    worst_wear_pct: 78,
    worst_component: 'Chain',
  },
];

const COMPONENTS = [
  {
    id: 'comp1',
    component_type: 'Chain',
    brand: 'Shimano',
    model: 'XT CN-M8100',
    installed_at_km: 2400,
    current_km: 800,
    max_km: 2000,
    wear_pct: 40,
    status: 'ok',
  },
  {
    id: 'comp2',
    component_type: 'Brake Pads',
    brand: 'Magura',
    model: 'MT5 Organic',
    installed_at_km: 2800,
    current_km: 400,
    max_km: 500,
    wear_pct: 90,
    status: 'critical',
  },
];

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/bikes', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: BIKES, meta: META }),
    });
  });
  await page.route('**/api/v1/bikes/bike1/components', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: COMPONENTS, meta: META }),
    });
  });
});

test.describe('Bike Page', () => {
  test('Bike list shows bike card', async ({ page }) => {
    await page.goto('/bike');
    await expect(page.getByRole('heading', { name: 'Bike Garage' })).toBeVisible();
    await expect(page.getByText('Spectral 125')).toBeVisible();
    await expect(page.getByText('Trail')).toBeVisible();
    await expect(page.getByText('3.200 km gesamt')).toBeVisible();
  });

  test('Components with wear percentage shown', async ({ page }) => {
    await page.goto('/bike');
    // Click the bike card to expand components
    await page.getByText('Spectral 125').click();
    await expect(page.getByText('Komponenten - Spectral 125')).toBeVisible();
    const wearBars = page.getByTestId('component-wear');
    await expect(wearBars).toHaveCount(2);
    await expect(page.getByText('Chain')).toBeVisible();
    await expect(page.getByText('40%')).toBeVisible();
    await expect(page.getByText('Brake Pads')).toBeVisible();
    await expect(page.getByText('90%')).toBeVisible();
  });

  test('"Fahrt loggen" button opens modal', async ({ page }) => {
    await page.goto('/bike');
    await page.getByRole('button', { name: 'Fahrt loggen' }).click();
    // Modal title
    await expect(page.getByRole('heading', { name: 'Fahrt loggen' })).toBeVisible();
    // Distance input
    await expect(page.getByPlaceholder('z.B. 42')).toBeVisible();
    // Save button
    await expect(page.getByRole('button', { name: 'Speichern' })).toBeVisible();
  });

  test('"Service" button opens modal', async ({ page }) => {
    await page.goto('/bike');
    await page.getByRole('button', { name: 'Service' }).click();
    // Modal title
    await expect(page.getByRole('heading', { name: 'Service loggen' })).toBeVisible();
    // Component select
    await expect(page.getByRole('combobox')).toBeVisible();
    // Action input
    await expect(page.getByPlaceholder('replaced / cleaned / lubed')).toBeVisible();
  });

  test('Progress bars have correct color (green for low wear, red for high)', async ({ page }) => {
    await page.goto('/bike');
    // Click to show components
    await page.getByText('Spectral 125').click();
    await expect(page.getByTestId('component-wear')).toHaveCount(2);

    // The ProgressBar component uses CSS classes: progress-green (<60%), progress-yellow (60-85%), progress-red (>=85%)
    // Chain at 40% should be green
    const chainBar = page.getByTestId('component-wear').filter({ hasText: 'Chain' }).locator('.progress-green');
    await expect(chainBar).toBeVisible();

    // Brake Pads at 90% should be red
    const brakeBar = page.getByTestId('component-wear').filter({ hasText: 'Brake Pads' }).locator('.progress-red');
    await expect(brakeBar).toBeVisible();
  });
});
