import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/weather/:path*",
        destination: "http://127.0.0.1:8000/weather/:path*",
      },
      {
        source: "/dispersion/:path*",
        destination: "http://127.0.0.1:8000/dispersion/:path*",
      },
      {
        source: "/events/:path*",
        destination: "http://127.0.0.1:8000/events/:path*",
      },
      {
        source: "/forests/:path*",
        destination: "http://127.0.0.1:8000/forests/:path*",
      },
      {
        source: "/gis/:path*",
        destination: "http://127.0.0.1:8000/gis/:path*",
      },
    ];
  },
};

export default nextConfig;
