import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Strict mode catches subtle React bugs early
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },

  // Expose only explicitly prefixed vars to the browser
  // Never put secrets here — only NEXT_PUBLIC_* vars
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  },

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "framerusercontent.com",
      },
    ],
  },

  experimental: {
    optimizePackageImports: ["lucide-react", "@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu", "@radix-ui/react-select"],
  },

  webpack: (config, { dev }) => {
    if (dev) {
      // Avoid filesystem cache serialization overhead across Docker Windows bind mounts
      config.cache = {
        type: "memory",
      };
    }
    return config;
  },

  // Rewrites proxy /api/v1/* to the FastAPI backend during local dev,
  // so the browser never makes cross-origin requests in dev.
  async rewrites() {
    const backendUrl = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
