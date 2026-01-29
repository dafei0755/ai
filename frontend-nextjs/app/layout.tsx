import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { SessionProvider } from "@/contexts/SessionContext";
import DevModeIndicator from "@/components/ui/DevModeIndicator";

export const metadata: Metadata = {
  title: "智能项目分析系统",
  description: "基于 LangGraph 多智能体协作的智能项目分析系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <ThemeProvider>
          <AuthProvider>
            <SessionProvider>
              {children}
              {/* 🆕 v7.277: 开发模式指示器 */}
              <DevModeIndicator />
            </SessionProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
