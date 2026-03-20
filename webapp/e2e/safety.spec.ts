import { test, expect } from '@playwright/test';

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

const ACTIVE_TIMER = {
  timer_id: 'timer-abc123',
  status: 'active',
  remaining_minutes: 85,
  ride_description: 'Trail-Runde Frankenjura',
  started_at: '2026-03-20T09:00:00Z',
  expires_at: '2026-03-20T11:00:00Z',
  emergency_contact: '+49 170 1234567',
};

const NO_TIMER = {
  timer_id: '',
  status: 'inactive',
  remaining_minutes: 0,
  ride_description: '',
  started_at: '2026-03-20T00:00:00Z',
  expires_at: '2026-03-20T00:00:00Z',
  emergency_contact: '',
};

test.describe('Safety Page', () => {
  test('Timer status is displayed when active', async ({ page }) => {
    await page.route('**/api/v1/safety/timer', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: ACTIVE_TIMER, meta: META }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: { message: 'ok' }, meta: META }),
        });
      }
    });

    await page.goto('/safety');
    await expect(page.getByText('Aktiver Timer')).toBeVisible();
    await expect(page.getByText('85 min')).toBeVisible();
    await expect(page.getByText('Trail-Runde Frankenjura')).toBeVisible();
    await expect(page.getByText('aktiv')).toBeVisible();
    await expect(page.getByText('+49 170 1234567')).toBeVisible();
  });

  test('"Neuer Timer" button opens modal when no timer', async ({ page }) => {
    await page.route('**/api/v1/safety/timer', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: NO_TIMER, meta: META }),
      });
    });

    await page.goto('/safety');
    await expect(page.getByText('Kein aktiver Timer')).toBeVisible();
    await page.getByRole('button', { name: 'Neuer Timer' }).click();
    // Modal should be visible
    await expect(page.getByRole('heading', { name: 'Neuer Timer' })).toBeVisible();
    await expect(page.getByPlaceholder('z.B. 120')).toBeVisible();
    await expect(page.getByPlaceholder('z.B. Trail-Runde Frankenjura')).toBeVisible();
  });

  test('Timer can be set via modal', async ({ page }) => {
    let timerStarted = false;
    await page.route('**/api/v1/safety/timer', async (route) => {
      if (route.request().method() === 'POST') {
        timerStarted = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: ACTIVE_TIMER, meta: META }),
        });
      } else {
        // GET: return active timer if started, inactive otherwise
        const data = timerStarted ? ACTIVE_TIMER : NO_TIMER;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data, meta: META }),
        });
      }
    });

    await page.goto('/safety');
    await expect(page.getByText('Kein aktiver Timer')).toBeVisible();

    // Open modal and fill form
    await page.getByRole('button', { name: 'Neuer Timer' }).click();
    await page.getByPlaceholder('z.B. 120').fill('120');
    await page.getByPlaceholder('z.B. Trail-Runde Frankenjura').fill('Trail-Runde Frankenjura');
    await page.getByPlaceholder('optional, z.B. +49 170 1234567').fill('+49 170 1234567');

    // Submit
    await page.getByRole('button', { name: 'Timer starten' }).click();

    // After submission, the page should reload and show the active timer
    await expect(page.getByText('Aktiver Timer')).toBeVisible();
    await expect(page.getByText('85 min')).toBeVisible();
  });

  test('"Entwarnung" button is visible when timer active', async ({ page }) => {
    await page.route('**/api/v1/safety/timer**', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: ACTIVE_TIMER, meta: META }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok', data: { message: 'cancelled' }, meta: META }),
        });
      }
    });

    await page.goto('/safety');
    await expect(page.getByText('Aktiver Timer')).toBeVisible();
    const entwarnungButton = page.getByRole('button', { name: 'Entwarnung' });
    await expect(entwarnungButton).toBeVisible();
  });
});
