import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Strict mode catches subtle React bugs early
  reactStrictMode: true,

  // Expose only explicitly prefixed vars to the browser
  // Never put secrets here — only NEXT_PUBLIC_* vars
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  },

  // Rewrites proxy /api/v1/* to the FastAPI backend during local dev,
  // so the browser never makes cross-origin requests in dev.
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
