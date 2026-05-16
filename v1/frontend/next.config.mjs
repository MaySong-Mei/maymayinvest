/** @type {import('next').NextConfig} */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // Proxy /api/v1/* to the FastAPI backend so the browser never CORS-hits it.
      { source: "/api/v1/:path*", destination: `${API_BASE}/api/v1/:path*` },
    ];
  },
};

export default nextConfig;
