import { test, expect } from '@playwright/test';

// Mock the dashboard API so the home page renders without a real backend
const DASHBOARD_MOCK = {
  status: 'ok',
  data: {
    ride_score: { score: 70, verdict: 'Good', weather_score: 30, trail_score: 20, wind_score: 10, daylight_score: 10, penalties: [] },
    weather_current: { temp_c: 15, wind_speed_kmh: 10, condition: 'sunny', humidity_pct: 55, precipitation_mm: 0 },
    trail_condition: { surface: 'dirt', condition: 'dry', confidence: 'high', rain_48h_mm: 0 },
    weekend_preview: { saturday: { score: 80, condition: 'sunny', temp_range: '10-20' }, sunday: { score: 60, condition: 'cloudy', temp_range: '8-16' } },
    next_service: null,
    active_timer: null,
  },
  meta: { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' },
};

test.beforeEach(async ({ page }) => {
  // Intercept all API calls with safe defaults
  await page.route('**/api/v1/dashboard', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DASHBOARD_MOCK) });
  });
  await page.route('**/api/v1/trails**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok', data: [], meta: { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' } }) });
  });
  await page.route('**/api/v1/tours/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok', data: [], meta: { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' } }) });
  });
  await page.route('**/api/v1/weather/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok', data: {}, meta: { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' } }) });
  });
  await page.route('**/api/v1/bikes**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok', data: [], meta: { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' } }) });
  });
  await page.route('**/api/v1/training/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok', data: {}, meta: { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' } }) });
  });
  await page.route('**/api/v1/safety/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok', data: { status: 'inactive' }, meta: { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' } }) });
  });
});

test.describe('Navigation', () => {
  test('dashboard is the default route (/)', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/');
    await expect(page.getByText('Ride Score')).toBeVisible();
  });

  test('navigation to /tours via bottom nav', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Touren' }).click();
    await expect(page).toHaveURL('/tours');
    await expect(page.getByRole('heading', { name: 'Touren' })).toBeVisible();
  });

  test('navigation to /trails via bottom nav', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Trails' }).click();
    await expect(page).toHaveURL('/trails');
    await expect(page.getByRole('heading', { name: 'Trails' })).toBeVisible();
  });

  test('navigation to /weather via bottom nav', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Wetter' }).click();
    await expect(page).toHaveURL('/weather');
    await expect(page.getByRole('heading', { name: 'Wetter' })).toBeVisible();
  });

  test('More menu opens and shows Bike, Training, eBike, Sicherheit', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'More' }).click();
    await expect(page.getByRole('link', { name: 'Bike' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Training' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'eBike' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Sicherheit' })).toBeVisible();
  });

  test('navigation to /bike via More menu', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'More' }).click();
    await page.getByRole('link', { name: 'Bike' }).click();
    await expect(page).toHaveURL('/bike');
    await expect(page.getByRole('heading', { name: 'Bike Garage' })).toBeVisible();
  });

  test('URL changes correctly on navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/');

    await page.getByRole('link', { name: 'Touren' }).click();
    await expect(page).toHaveURL('/tours');

    await page.getByRole('link', { name: 'Trails' }).click();
    await expect(page).toHaveURL('/trails');

    await page.getByRole('link', { name: 'Wetter' }).click();
    await expect(page).toHaveURL('/weather');

    await page.getByRole('link', { name: 'Home' }).click();
    await expect(page).toHaveURL('/');
  });

  test('back button works (go to /weather, then back to /)', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Wetter' }).click();
    await expect(page).toHaveURL('/weather');

    await page.goBack();
    await expect(page).toHaveURL('/');
    await expect(page.getByText('Ride Score')).toBeVisible();
  });
});
