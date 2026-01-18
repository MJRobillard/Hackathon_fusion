import type { NextConfig } from "next";

// Backend URL for Next.js rewrites (server-side proxy)
// Note: This is only used for server-side rendering. Client-side code uses
// the BackendUrlProvider which allows users to toggle between local/remote.
// Server-side rewrites won't work for localhost when deployed on Vercel,
// but client-side code will connect directly to the configured URL.
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
