/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 确保与后端 API 的连接
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
