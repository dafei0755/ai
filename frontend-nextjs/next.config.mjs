const backendApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack(config) {
    config.resolve.alias = {
      ...(config.resolve.alias ?? {}),
      canvas: false,
    };
    return config;
  },
  // API代理配置（开发环境）
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendApiUrl}/api/:path*`,
      },
      // 🔥 v7.120: 代理静态图片请求到 FastAPI 服务器
      {
        source: '/generated_images/:path*',
        destination: `${backendApiUrl}/generated_images/:path*`,
      },
      {
        source: '/followup_images/:path*',
        destination: `${backendApiUrl}/followup_images/:path*`,
      },
      {
        source: '/archived_images/:path*',
        destination: `${backendApiUrl}/archived_images/:path*`,
      },
      {
        source: '/uploads/:path*',
        destination: `${backendApiUrl}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
