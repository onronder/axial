/**
 * Next.js Middleware Entry Point
 * 
 * This file is the entry point for Next.js middleware.
 * It imports the proxy implementation from proxy.ts and exports it
 * with the correct name that Next.js expects.
 * 
 * @see https://nextjs.org/docs/app/building-your-application/routing/middleware
 */

import { proxy, config as proxyConfig } from './proxy'

// Next.js requires the middleware function to be named 'middleware'
export const middleware = proxy

// Export the matcher configuration
export const config = proxyConfig
