/**
 * URL Validation Utilities
 *
 * Security utilities for validating external URLs before redirecting.
 * Prevents open redirect vulnerabilities by enforcing trusted domains.
 */

/**
 * Trusted domains for checkout/billing redirects.
 * Only HTTPS URLs on these domains are allowed.
 */
const TRUSTED_CHECKOUT_DOMAINS = [
    'polar.sh',
    'checkout.polar.sh',
    'axiohub.io',
];

/**
 * Validates that a URL is a safe checkout redirect destination.
 *
 * @param url - The URL to validate
 * @returns true if the URL is a trusted HTTPS checkout URL
 *
 * Security checks:
 * - Must be a valid URL
 * - Must use HTTPS protocol
 * - Must be on a trusted domain or subdomain
 */
export function isValidCheckoutUrl(url: string): boolean {
    try {
        const parsed = new URL(url);

        // Require HTTPS
        if (parsed.protocol !== 'https:') {
            return false;
        }

        // Check if hostname matches or is a subdomain of trusted domains
        return TRUSTED_CHECKOUT_DOMAINS.some(
            (domain) =>
                parsed.hostname === domain ||
                parsed.hostname.endsWith(`.${domain}`)
        );
    } catch {
        // Invalid URL
        return false;
    }
}
