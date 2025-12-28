import { Page } from '@playwright/test';

export const generateRandomUser = () => {
    const uniqueId = Date.now().toString(36) + Math.random().toString(36).substring(2);
    return {
        firstName: `Test${uniqueId}`,
        lastName: 'User',
        email: `test.${uniqueId}@example.com`,
        password: 'Password123!',
    };
};

export const bypassPaywall = async (page: Page) => {
    // This helper is a placeholder for when we implement a way to bypass the paywall
    // in a test environment (e.g., via a backdoor API or checking a specific element).
    // For now, we mainly assert the paywall presence.
    await page.waitForSelector('text=Choose Plan');
};
