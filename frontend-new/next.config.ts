import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Production optimizations
  compress: true, // Enable gzip/brotli compression

  // Optimize package imports for tree-shaking
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "@radix-ui/react-dialog",
      "@radix-ui/react-popover",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-tabs",
      "@radix-ui/react-scroll-area",
      "@radix-ui/react-tooltip",
      "recharts",
      "date-fns",
    ],
  },

  // Image optimization
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    minimumCacheTTL: 60,
    // External image domains for next/image optimization
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'img.youtube.com',
        pathname: '/vi/**',
      },
      {
        protocol: 'https',
        hostname: 'www.google.com',
        pathname: '/s2/favicons**',
      },
      {
        protocol: 'https',
        hostname: '*.googleusercontent.com',
      },
      {
        protocol: 'https',
        hostname: 'www.notion.so',
      },
    ],
  },

  // Headers for security and caching
  async headers() {
    // Build CSP directives for production-grade security
    // @see https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://*.supabase.co';
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://axial-production-1503.up.railway.app';
    
    // CSP directives - carefully crafted for security + functionality
    const cspDirectives = [
      // Default: only same origin
      "default-src 'self'",
      
      // Scripts: self + inline for Next.js hydration + eval for dev tools (removed in prod ideally)
      // 'unsafe-inline' needed for Next.js script tags, 'unsafe-eval' for development
      process.env.NODE_ENV === 'development'
        ? "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.sentry-cdn.com https://browser.sentry-cdn.com"
        : "script-src 'self' 'unsafe-inline' https://js.sentry-cdn.com https://browser.sentry-cdn.com",
      
      // Styles: self + inline for Tailwind/styled components
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      
      // Fonts: self + Google Fonts
      "font-src 'self' https://fonts.gstatic.com data:",
      
      // Images: self + approved domains for avatars, thumbnails, favicons
      `img-src 'self' data: blob: https://img.youtube.com https://www.google.com https://*.googleusercontent.com https://www.notion.so ${supabaseUrl}`,
      
      // Connect: API endpoints + Supabase + Sentry
      `connect-src 'self' ${apiUrl} ${supabaseUrl} https://*.supabase.co wss://*.supabase.co https://*.sentry.io https://o4509311565545472.ingest.us.sentry.io`,
      
      // Frames: deny all framing (clickjacking protection)
      "frame-ancestors 'none'",
      
      // Object/embed: none (prevents Flash/plugin exploits)
      "object-src 'none'",
      
      // Base URI: only self (prevents base tag injection)
      "base-uri 'self'",
      
      // Form action: only self (prevents form hijacking)
      "form-action 'self'",
      
      // Upgrade insecure requests in production
      process.env.NODE_ENV === 'production' ? "upgrade-insecure-requests" : "",
    ].filter(Boolean).join('; ');
    
    return [
      // Security headers for all routes
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: cspDirectives,
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            // Prevent MIME type sniffing
            key: "X-Download-Options",
            value: "noopen",
          },
          {
            // Cross-Origin policies for modern security
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin",
          },
        ],
      },
      // Caching for static assets
      {
        source: "/:all*(svg|jpg|png|webp|avif)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },

  // API proxying for backend
  async rewrites() {
    const rawApiBase = process.env.NEXT_PUBLIC_API_URL || "https://axial-production-1503.up.railway.app";
    const trimmedApiBase = rawApiBase.replace(/\/$/, "");
    const productionApiBase = trimmedApiBase.replace(/\/api\/v1\/?$/i, "");

    return [
      {
        source: '/api/py/:path*',
        destination: process.env.NODE_ENV === 'development'
          ? 'http://127.0.0.1:8000/api/v1/:path*'
          : `${productionApiBase}/api/v1/:path*`,
      },
    ];
  },
};

// NOTE: withSentryConfig removed for Turbopack compatibility (Next.js 16)
// Sentry error tracking still works via sentry.client.config.ts runtime initialization
// Source maps are NOT uploaded during build - errors will have minified stack traces

export default withSentryConfig(nextConfig, {
  // For all available options, see:
  // https://www.npmjs.com/package/@sentry/webpack-plugin#options

  org: "fittechs",

  project: "axiohub-frontend",

  // Only print logs for uploading source maps in CI
  silent: !process.env.CI,

  // For all available options, see:
  // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

  // Upload a larger set of source maps for prettier stack traces (increases build time)
  widenClientFileUpload: true,

  // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers.
  // This can increase your server load as well as your hosting bill.
  // Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
  // side errors will fail.
  tunnelRoute: "/monitoring",

  webpack: {
    // Enables automatic instrumentation of Vercel Cron Monitors. (Does not yet work with App Router route handlers.)
    // See the following for more information:
    // https://docs.sentry.io/product/crons/
    // https://vercel.com/docs/cron-jobs
    automaticVercelMonitors: true,

    // Tree-shaking options for reducing bundle size
    treeshake: {
      // Automatically tree-shake Sentry logger statements to reduce bundle size
      removeDebugLogging: true,
    },
  },
});
