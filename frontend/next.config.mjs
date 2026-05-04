/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/agent/:path*",
        destination: "http://localhost:8091/api/v1/agent/:path*",
      },
    ];
  },
};

export default nextConfig;
