import type { NextConfig } from "next";

// Backend URL for Next.js rewrites (server-side proxy)
// This reads from BUILD-time env var set by Dockerfile
// In Docker, default to backend service name; locally, use localhost
const backendUrl =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://localhost:8000');

const nextConfig: NextConfig = {
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
