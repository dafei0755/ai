/**
 * Next.js Middleware - 路由保护
 * 检查用户是否已登录，未登录用户跳转到登录页
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 登录页和静态资源不需要保护
  if (
    pathname.startsWith('/auth/login') ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.') // 静态文件（.js, .css, .png 等）
  ) {
    return NextResponse.next();
  }

  // 检查是否有 JWT Token（从 Cookie 或将来的其他存储）
  const token = request.cookies.get('wp_jwt_token')?.value;

  // 注意：由于 Token 存储在 localStorage，这里无法直接验证
  // 实际验证会在客户端 AuthContext 中进行
  // 这里主要是一个额外的保护层（可选）

  // 如果需要服务端验证，需要将 Token 存储在 Cookie 中
  // 目前让客户端 AuthContext 处理跳转逻辑
  
  return NextResponse.next();
}

// 配置需要保护的路由（排除登录页）
export const config = {
  matcher: [
    /*
     * 匹配所有路径，除了：
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
