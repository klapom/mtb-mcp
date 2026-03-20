import { test, expect } from '@playwright/test';

const DASHBOARD_DATA = {
  ride_score: {
    score: 85,
    verdict: 'Great',
    weather_score: 35,
    trail_score: 25,
    wind_score: 15,
    daylight_score: 10,
    penalties: [],
  },
  weather_current: {
    temp_c: 14,
    wind_speed_kmh: 12,
    condition: 'cloudy',
    humidity_pct: 60,
    precipitation_mm: 0,
  },
  trail_condition: {
    surface: 'dirt',
    condition: 'dry',
    confidence: 'high',
    rain_48h_mm: 0,
  },
  weekend_preview: {
    saturday: { score: 90, condition: 'sunny', temp_range: '8-18' },
    sunday: { score: 75, condition: 'cloudy', temp_range: '6-14' },
  },
  next_service: {
    component: 'Chain',
    bike_name: 'Spectral',
    wear_pct: 65,
    km_remaining: 500,
    status: 'warning',
  },
  active_timer: null,
};

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/dashboard', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', data: DASHBOARD_DATA, meta: META }),
    });
  });
});

test.describe('Dashboard', () => {
  test('Ride Score gauge shows "85"', async ({ page }) => {
    await page.goto('/');
    const scoreValue = page.getByTestId('ride-score-value');
    await expect(scoreValue).toBeVisible();
    await expect(scoreValue).toHaveText('85');
  });

  test('Weather strip shows temperature "14°C"', async ({ page }) => {
    await page.goto('/');
    const weatherTemp = page.getByTestId('weather-temp');
    await expect(weatherTemp).toBeVisible();
    await expect(weatherTemp).toHaveText('14°C');
  });

  test('Trail condition shows "dry" badge', async ({ page }) => {
    await page.goto('/');
    // The trail condition card shows a Badge with the condition text
    const trailConditionCard = page.locator('text=Trail Zustand').locator('..');
    await expect(trailConditionCard).toBeVisible();
    await expect(page.getByText('dry')).toBeVisible();
  });

  test('Weekend preview shows Saturday and Sunday scores', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Samstag')).toBeVisible();
    await expect(page.getByText('Sonntag')).toBeVisible();
    await expect(page.getByText('90')).toBeVisible();
    await expect(page.getByText('75')).toBeVisible();
  });

  test('Next Service card visible with "Chain" and "Spectral"', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Nächster Service')).toBeVisible();
    await expect(page.getByText('Chain')).toBeVisible();
    await expect(page.getByText('Spectral')).toBeVisible();
    await expect(page.getByText('500 km verbleibend')).toBeVisible();
  });

  test('Quick action buttons are visible and link correctly', async ({ page }) => {
    await page.goto('/');
    // The quick actions: Wetter, Trails, Touren, Bike
    const wetterAction = page.locator('a[href="/weather"]', { hasText: 'Wetter' });
    const trailsAction = page.locator('a[href="/trails"]', { hasText: 'Trails' });
    const tourenAction = page.locator('a[href="/tours"]', { hasText: 'Touren' });
    const bikeAction = page.locator('a[href="/bike"]', { hasText: 'Bike' });

    await expect(wetterAction).toBeVisible();
    await expect(trailsAction).toBeVisible();
    await expect(tourenAction).toBeVisible();
    await expect(bikeAction).toBeVisible();

    // Verify one of the links navigates correctly
    await page.route('**/api/v1/weather/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: {}, meta: META }),
      });
    });
    await wetterAction.click();
    await expect(page).toHaveURL('/weather');
  });
});
