import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/py/:path*',
        destination: 'https://axial-production-1503.up.railway.app/:path*',
      },
    ];
  },
};

export default nextConfig;
