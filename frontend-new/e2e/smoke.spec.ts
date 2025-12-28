import { test, expect } from '@playwright/test';
import { generateRandomUser } from './utils';

test.describe('Smoke Tests', () => {
    test('New user registration flow shows paywall', async ({ page }) => {
        const user = generateRandomUser();

        // 1. Go to Register page
        await page.goto('/register');

        // 2. Fill Form
        await page.fill('input[name="firstName"]', user.firstName);
        await page.fill('input[name="lastName"]', user.lastName);
        await page.fill('input[name="email"]', user.email);
        await page.fill('input[name="password"]', user.password);

        // Accept Terms (if checkbox exists)
        // Assuming checkbox has id or name 'terms' or 'termsAccepted'
        const termsCheckbox = page.locator('button[role="checkbox"]').first();
        if (await termsCheckbox.isVisible()) {
            await termsCheckbox.click();
        }

        // 3. Submit
        await page.click('button[type="submit"]');

        // 4. Assert Redirect to Dashboard (or Paywall directly)
        // The PaywallGuard might render on the dashboard route
        await expect(page).toHaveURL(/\/dashboard/);

        // 5. Assert Paywall Content
        // Look for "Choose Your Plan" or similar text from UseWarningBanner/PaywallGuard
        // Update text based on actual Paywall component content
        // Wait for usage check to complete (loader to disappear)
        await expect(page.locator("text=Choose Your Plan")).toBeVisible({ timeout: 15000 });
    });

    test('Protected routes redirect to login if unauthenticated', async ({ page }) => {
        await page.goto('/dashboard/settings');
        await expect(page).toHaveURL(/\/login/);
    });
});
