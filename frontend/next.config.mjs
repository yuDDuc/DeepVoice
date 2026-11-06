const backend = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  turbopack: { root: import.meta.dirname },
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` },
      { source: "/ws/v1", destination: `${backend}/ws/v1` },
    ];
  },
};
export default nextConfig;
