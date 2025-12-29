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
  },

  // Headers for caching static assets
  async headers() {
    return [
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
        destination: process.env.NODE_ENV === 'development'
          ? 'http://127.0.0.1:8000/api/v1/:path*'
          : 'https://axial-production-1503.up.railway.app/api/v1/:path*',
      },
    ];
  },
};

// NOTE: withSentryConfig removed for Turbopack compatibility (Next.js 16)
// Sentry error tracking still works via sentry.client.config.ts runtime initialization
// Source maps are NOT uploaded during build - errors will have minified stack traces

export default nextConfig;
