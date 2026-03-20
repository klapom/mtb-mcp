import { test, expect } from '@playwright/test';

const META = { request_id: 'test', duration_ms: 1, timestamp: '2026-03-20T00:00:00Z' };

const FITNESS_DATA = {
  ctl: 45,
  atl: 50,
  tsb: -5,
  fitness_level: 'moderate',
  trend: 'up',
};

const GOALS_DATA = [
  {
    id: 'goal1',
    name: 'Frankenjura Marathon',
    target_date: '2026-06-15',
    goal_type: 'race',
    status: 'active',
    progress_pct: 62,
  },
];

test.describe('Training Page', () => {
  test('Training status shows CTL/ATL/TSB values', async ({ page }) => {
    await page.route('**/api/v1/training/fitness', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: FITNESS_DATA, meta: META }),
      });
    });
    await page.route('**/api/v1/training/goals', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: GOALS_DATA, meta: META }),
      });
    });

    await page.goto('/training');
    await expect(page.getByText('Fitness-Status')).toBeVisible();
    // CTL = 45.0
    await expect(page.getByText('CTL')).toBeVisible();
    await expect(page.getByText('45.0')).toBeVisible();
    // ATL = 50.0
    await expect(page.getByText('ATL')).toBeVisible();
    await expect(page.getByText('50.0')).toBeVisible();
    // TSB = -5.0
    await expect(page.getByText('TSB')).toBeVisible();
    await expect(page.getByText('-5.0')).toBeVisible();
  });

  test('Active goal is visible with name and progress', async ({ page }) => {
    await page.route('**/api/v1/training/fitness', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: FITNESS_DATA, meta: META }),
      });
    });
    await page.route('**/api/v1/training/goals', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: GOALS_DATA, meta: META }),
      });
    });

    await page.goto('/training');
    await expect(page.getByText('Aktive Ziele')).toBeVisible();
    await expect(page.getByText('Frankenjura Marathon')).toBeVisible();
    await expect(page.getByText('active')).toBeVisible();
    await expect(page.getByText('62%')).toBeVisible();
  });

  test('Progress bar shown for goal', async ({ page }) => {
    await page.route('**/api/v1/training/fitness', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: FITNESS_DATA, meta: META }),
      });
    });
    await page.route('**/api/v1/training/goals', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: GOALS_DATA, meta: META }),
      });
    });

    await page.goto('/training');
    // The ProgressBar component for 62% should use progress-yellow (between 60-85%)
    const goalCard = page.locator('text=Frankenjura Marathon').locator('..').locator('..');
    await expect(goalCard).toBeVisible();
    // Verify a progress bar element exists within the goal area
    const progressBar = page.locator('.progress-yellow');
    await expect(progressBar.first()).toBeVisible();
  });

  test('Empty state when no goals', async ({ page }) => {
    await page.route('**/api/v1/training/fitness', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: FITNESS_DATA, meta: META }),
      });
    });
    await page.route('**/api/v1/training/goals', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', data: [], meta: META }),
      });
    });

    await page.goto('/training');
    await expect(page.getByText('Kein aktives Ziel')).toBeVisible();
  });
});
