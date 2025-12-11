import type { Metadata } from "next";
import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}
