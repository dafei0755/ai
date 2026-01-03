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
      // 🔥 v7.120: 代理静态图片请求到 FastAPI 服务器
      {
        source: '/generated_images/:path*',
        destination: 'http://127.0.0.1:8000/generated_images/:path*',
      },
      {
        source: '/followup_images/:path*',
        destination: 'http://127.0.0.1:8000/followup_images/:path*',
      },
      {
        source: '/archived_images/:path*',
        destination: 'http://127.0.0.1:8000/archived_images/:path*',
      },
      {
        source: '/uploads/:path*',
        destination: 'http://127.0.0.1:8000/uploads/:path*',
      },
    ];
  },
};

export default nextConfig;
