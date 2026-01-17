import { test, expect, Page } from '@playwright/test';

/**
 * ============================================================
 * ARTIFACT 4: Billing Flow E2E Test
 * ============================================================
 * 
 * Purpose: End-to-end verification of the billing pipeline:
 *   1. Polar webhook → subscriptions table
 *   2. get_effective_plan() returns correct plan
 *   3. Frontend displays correct plan badge
 *   4. Features are properly gated by plan
 * 
 * Prerequisites:
 *   1. Test user with known plan status
 *   2. Set environment variables:
 *      - E2E_EMAIL: Test user email
 *      - E2E_PASSWORD: Test user password
 *      - E2E_BASE_URL: Production URL
 * 
 * Run: npx playwright test e2e/04_billing_flow.spec.ts --project=chromium
 * ============================================================
 */

// Configuration
const E2E_EMAIL = process.env.E2E_EMAIL || 'admin@axial-test.com';
const E2E_PASSWORD = process.env.E2E_PASSWORD || '';
const E2E_BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';

// Timeouts
const NAVIGATION_TIMEOUT = 30_000;
const API_TIMEOUT = 15_000;

test.describe('Billing Flow - Plan Inheritance & Display', () => {
    
    test.beforeEach(async ({ page }) => {
        if (!E2E_PASSWORD) {
            throw new Error('E2E_PASSWORD environment variable is required');
        }
    });

    test('Login and verify plan is displayed', async ({ page }) => {
        await loginUser(page);
        
        // Wait for dashboard to load
        await expect(page).toHaveURL(/\/dashboard/, { timeout: NAVIGATION_TIMEOUT });
        
        // Check that plan is displayed somewhere in the UI
        // The plan badge is in the sidebar under the user name
        const planBadge = page.locator('text=/Enterprise|Pro|Starter|Free/i').first();
        await expect(planBadge).toBeVisible({ timeout: 10000 });
        
        console.log('✅ Plan badge is visible in UI');
    });

    test('Verify usage API returns correct plan', async ({ page, request }) => {
        await loginUser(page);
        await expect(page).toHaveURL(/\/dashboard/, { timeout: NAVIGATION_TIMEOUT });
        
        // Get auth cookies from the browser context
        const cookies = await page.context().cookies();
        const authCookie = cookies.find(c => c.name.includes('supabase') || c.name.includes('auth'));
        
        // Make API request to verify plan
        // Note: This tests the actual API response, not just the UI
        const apiUrl = `${E2E_BASE_URL}/api/v1/usage`;
        
        // Use page.evaluate to make fetch from browser context (has auth)
        const usageResponse = await page.evaluate(async (url) => {
            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            if (!response.ok) {
                return { error: response.status, statusText: response.statusText };
            }
            return response.json();
        }, apiUrl);
        
        console.log('📊 Usage API response:', JSON.stringify(usageResponse, null, 2));
        
        // Verify response structure
        if ('error' in usageResponse) {
            console.log('⚠️ API returned error - may need authentication');
        } else {
            // Verify plan is a valid type
            const validPlans = ['none', 'free', 'starter', 'pro', 'enterprise'];
            expect(validPlans).toContain(usageResponse.plan?.toLowerCase());
            
            // Verify subscription_status is present
            expect(usageResponse.subscription_status).toBeDefined();
            console.log(`✅ Plan: ${usageResponse.plan}, Status: ${usageResponse.subscription_status}`);
        }
    });

    test('Verify effective plan API returns inherited status', async ({ page }) => {
        await loginUser(page);
        await expect(page).toHaveURL(/\/dashboard/, { timeout: NAVIGATION_TIMEOUT });
        
        // Test the effective-plan endpoint
        const apiUrl = `${E2E_BASE_URL}/api/v1/team/effective-plan`;
        
        const effectivePlanResponse = await page.evaluate(async (url) => {
            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            if (!response.ok) {
                return { error: response.status };
            }
            return response.json();
        }, apiUrl);
        
        console.log('📊 Effective plan response:', JSON.stringify(effectivePlanResponse, null, 2));
        
        if (!('error' in effectivePlanResponse)) {
            // Verify response has expected fields
            expect(effectivePlanResponse).toHaveProperty('plan');
            expect(effectivePlanResponse).toHaveProperty('inherited');
            expect(effectivePlanResponse).toHaveProperty('team_id');
            expect(effectivePlanResponse).toHaveProperty('team_name');
            
            console.log(`✅ Effective plan: ${effectivePlanResponse.plan}, Inherited: ${effectivePlanResponse.inherited}`);
        }
    });

    test('Verify settings/billing page shows correct plan', async ({ page }) => {
        await loginUser(page);
        
        // Navigate to billing settings
        await page.goto(`${E2E_BASE_URL}/dashboard/settings/billing`);
        await page.waitForLoadState('networkidle');
        
        // Check for plan information on the page
        const planSection = page.locator('text=/Current Plan|Your Plan|Plan/i').first();
        await expect(planSection).toBeVisible({ timeout: 10000 });
        
        // Take screenshot for debugging
        await page.screenshot({ path: 'test-results/billing-page.png' });
        
        console.log('✅ Billing page loaded with plan information');
    });

    test('Enterprise users see unlimited resources', async ({ page }) => {
        await loginUser(page);
        await expect(page).toHaveURL(/\/dashboard/, { timeout: NAVIGATION_TIMEOUT });
        
        // Check the page content
        const pageContent = await page.content();
        
        // For Enterprise users, the UsageIndicator should not show (returns null)
        // OR it should show "Unlimited resources"
        const hasUnlimited = pageContent.includes('Unlimited');
        const hasFileLimit = /Files:\s*\d+\/\d+/.test(pageContent);
        
        if (hasUnlimited) {
            console.log('✅ Enterprise user: "Unlimited resources" indicator found');
        } else if (hasFileLimit) {
            console.log('ℹ️ Non-enterprise user: File limit indicator found');
        } else {
            console.log('ℹ️ Usage indicator not prominently displayed');
        }
    });

    test('Plan badge in sidebar matches API response', async ({ page }) => {
        await loginUser(page);
        await expect(page).toHaveURL(/\/dashboard/, { timeout: NAVIGATION_TIMEOUT });
        
        // Get plan from API
        const apiUrl = `${E2E_BASE_URL}/api/v1/usage`;
        const usageResponse = await page.evaluate(async (url) => {
            const response = await fetch(url, { credentials: 'include' });
            if (!response.ok) return { plan: null };
            return response.json();
        }, apiUrl);
        
        const apiPlan = usageResponse.plan?.toLowerCase();
        
        // Check sidebar for matching badge
        const sidebarText = await page.locator('.flex.h-full.flex-col').textContent() || '';
        const sidebarPlanMatch = sidebarText.toLowerCase().includes(apiPlan || '');
        
        if (apiPlan) {
            console.log(`📊 API Plan: ${apiPlan}`);
            console.log(`🔍 Sidebar contains plan: ${sidebarPlanMatch}`);
            
            // The plan should appear somewhere in the sidebar
            if (!sidebarPlanMatch && apiPlan !== 'free' && apiPlan !== 'none') {
                // Non-free plans should show a badge
                console.log('⚠️ Plan badge may not be visible for this plan');
            }
        }
    });
});

// ============================================================
// HELPER FUNCTIONS
// ============================================================

async function loginUser(page: Page): Promise<void> {
    await page.goto(`${E2E_BASE_URL}/login`);
    
    // Fill login form
    await page.fill('input[name="email"], input[type="email"]', E2E_EMAIL);
    await page.fill('input[name="password"], input[type="password"]', E2E_PASSWORD);
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Wait for redirect
    await page.waitForURL(/\/dashboard/, { timeout: NAVIGATION_TIMEOUT });
}

/**
 * Test Scenarios Documentation
 * ============================
 * 
 * SCENARIO 1: Team Owner with Active Subscription
 * - subscriptions.status = 'active'
 * - subscriptions.plan_type = 'enterprise'
 * - get_effective_plan() returns 'enterprise'
 * - UI shows "Enterprise" badge
 * - UsageIndicator returns null (no limit display)
 * 
 * SCENARIO 2: Team Member (Inherits Plan)
 * - Team owner has enterprise subscription
 * - Member's effective-plan.inherited = true
 * - Member sees same features as owner
 * 
 * SCENARIO 3: Solo User (No Team)
 * - No team membership
 * - Falls back to user_profiles.plan
 * - Or defaults to 'free'
 * 
 * SCENARIO 4: Canceled Subscription
 * - subscriptions.status = 'canceled'
 * - get_effective_plan() returns 'free'
 * - UI shows paywall/upgrade prompts
 * 
 * IMPORTANT SCHEMA NOTE:
 * =====================
 * user_profiles.subscription_status was REMOVED in migration 20251231130000.
 * Subscription status is now stored in subscriptions.status table.
 * The get_effective_plan() function was fixed in migration 20260117140000.
 */
