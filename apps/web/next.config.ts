import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["globe.gl", "three-globe", "three-conic-polygon-geometry", "kframe", "three"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
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
