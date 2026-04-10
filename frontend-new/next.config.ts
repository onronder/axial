import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const LOCAL_API_BASE = "http://127.0.0.1:8000";

// Build-time validation of required environment variables
const requiredEnvVars = [
  'NEXT_PUBLIC_SUPABASE_URL',
  'NEXT_PUBLIC_SUPABASE_ANON_KEY',
] as const;

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    if (process.env.NODE_ENV === 'production' && !process.env.CI) {
      throw new Error(
        `Missing required environment variable: ${envVar}. ` +
        `Set it in your deployment environment.`
      );
    } else {
      console.warn(
        `⚠️  Missing environment variable: ${envVar}. ` +
        `Build will continue but runtime features may not work.`
      );
    }
  }
}

function resolveApiBaseUrl(): string {
  const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configuredApiUrl) {
    return configuredApiUrl.replace(/\/$/, "");
  }

  if (process.env.NODE_ENV === "production" && !process.env.CI) {
    throw new Error(
      "Missing required environment variable: NEXT_PUBLIC_API_URL. " +
      "Set it in your deployment environment."
    );
  }

  console.warn(
    "⚠️  Missing NEXT_PUBLIC_API_URL. " +
    `Falling back to ${LOCAL_API_BASE} outside production builds.`
  );
  return LOCAL_API_BASE;
}

const resolvedApiUrl = resolveApiBaseUrl();
const resolvedApiOrigin = resolvedApiUrl.replace(/\/api\/v1\/?$/i, "");

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
    
    // CSP directives - carefully crafted for security + functionality
    const cspDirectives = [
      // Default: only same origin
      "default-src 'self'",
      
      // Scripts: self + inline for Next.js hydration + eval for dev tools (removed in prod ideally)
      // 'unsafe-inline' needed for Next.js script tags, 'unsafe-eval' for development
      // vercel.live needed for Vercel preview feedback tool
      process.env.NODE_ENV === 'development'
        ? "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.sentry-cdn.com https://browser.sentry-cdn.com https://vercel.live"
        : "script-src 'self' 'unsafe-inline' https://js.sentry-cdn.com https://browser.sentry-cdn.com https://vercel.live",
      
      // Workers: allow blob URLs for web workers (e.g., PDF parsing, syntax highlighting)
      "worker-src 'self' blob:",
      
      // Styles: self + inline for Tailwind/styled components
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      
      // Fonts: self + Google Fonts
      "font-src 'self' https://fonts.gstatic.com data:",
      
      // Images: self + approved domains for avatars, thumbnails, favicons
      `img-src 'self' data: blob: https://img.youtube.com https://www.google.com https://*.googleusercontent.com https://www.notion.so ${supabaseUrl}`,
      
      // Connect: API endpoints + Supabase + Sentry
      `connect-src 'self' ${resolvedApiOrigin} ${supabaseUrl} https://*.supabase.co wss://*.supabase.co https://*.sentry.io https://o4509311565545472.ingest.us.sentry.io`,
      
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
          {
            // HSTS: Enforce HTTPS for 1 year, include subdomains, preload-eligible
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
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
    return [
      {
        source: '/api/py/:path*',
        destination: `${resolvedApiOrigin}/api/v1/:path*`,
      },
    ];
  },
};

// Sentry wraps the Next.js config to upload source maps during build.
// Source maps are deleted after upload to prevent 404 errors in browser DevTools.

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

  // Ignore Next.js internal files that don't have source maps
  // This suppresses warnings like "could not determine a source map reference"
  sourcemaps: {
    deleteSourcemapsAfterUpload: true,
    ignore: [
      "node_modules/**",
      // Next.js client reference manifests (React Server Components)
      "**/*_client-reference-manifest.js",
      "**/*_client-reference-manifest.js.map",
      // Next.js internal manifests
      "**/middleware-build-manifest.js",
      "**/server-reference-manifest.js",
      "**/next-font-manifest.js",
      "**/interception-route-rewrite-manifest.js",
      // Build artifacts without source maps
      "**/*.hot-update.js",
    ],
  },

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
