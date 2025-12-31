/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // API代理配置（开发环境）
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
