"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, Pagination, Navigation } from "swiper/modules";
import { Loader2, Settings } from "lucide-react";

// 导入 Swiper 样式
import "swiper/css";
import "swiper/css/pagination";
import "swiper/css/navigation";

interface ConceptImage {
  url: string;
  prompt: string;
  owner_role: string;
  created_at: string;
}

interface FeaturedSession {
  session_id: string;
  title: string;
  user_input: string;
  created_at: string;
  analysis_mode: string;
  concept_image: ConceptImage | null;
  status: string;
}

interface ShowcaseConfig {
  rotation_interval_seconds: number;
  autoplay: boolean;
  loop: boolean;
  show_navigation: boolean;
  show_pagination: boolean;
}

export default function ShowcasePage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<FeaturedSession[]>([]);
  const [config, setConfig] = useState<ShowcaseConfig>({
    rotation_interval_seconds: 5,
    autoplay: true,
    loop: true,
    show_navigation: true,
    show_pagination: true,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFeaturedSessions();
  }, []);

  const loadFeaturedSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get("/api/showcase/featured");
      setSessions(response.data.featured_sessions || []);
      setConfig(response.data.config || config);
    } catch (err: any) {
      console.error("加载精选展示失败:", err);
      setError(err.response?.data?.detail || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSlideClick = (sessionId: string) => {
    router.push(`/analysis/${sessionId}`);
  };

  const handleConfigClick = () => {
    router.push("/admin/showcase-config");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">加载精选展示...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center max-w-md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-800 mb-2">加载失败</h2>
            <p className="text-red-600 mb-4">{error}</p>
            <button
              onClick={loadFeaturedSessions}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
            >
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center max-w-md">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              暂无精选展示
            </h2>
            <p className="text-gray-600 mb-6">
              请先在配置页面添加精选会话
            </p>
            <button
              onClick={handleConfigClick}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 inline-flex items-center"
            >
              <Settings className="w-5 h-5 mr-2" />
              前往配置
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-screen bg-black">
      {/* 配置按钮 */}
      <button
        onClick={handleConfigClick}
        className="absolute top-4 right-4 z-50 bg-white/10 hover:bg-white/20 backdrop-blur-sm text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all"
      >
        <Settings className="w-5 h-5" />
        配置
      </button>

      {/* Swiper 轮播 */}
      <Swiper
        modules={[Autoplay, Pagination, Navigation]}
        spaceBetween={0}
        slidesPerView={1}
        autoplay={
          config.autoplay
            ? {
                delay: config.rotation_interval_seconds * 1000,
                disableOnInteraction: false,
              }
            : false
        }
        loop={config.loop}
        pagination={
          config.show_pagination
            ? {
                clickable: true,
                bulletClass: "swiper-pagination-bullet",
                bulletActiveClass: "swiper-pagination-bullet-active",
              }
            : false
        }
        navigation={config.show_navigation}
        className="w-full h-full"
        style={{
          "--swiper-navigation-color": "#fff",
          "--swiper-pagination-color": "#fff",
          "--swiper-pagination-bullet-inactive-color": "#fff",
          "--swiper-pagination-bullet-inactive-opacity": "0.5",
        } as React.CSSProperties}
      >
        {sessions.map((session, index) => (
          <SwiperSlide key={session.session_id}>
            <div
              onClick={() => handleSlideClick(session.session_id)}
              className="relative w-full h-full cursor-pointer group"
            >
              {/* 背景图片 */}
              {session.concept_image && (
                <div
                  className="absolute inset-0 bg-cover bg-center"
                  style={{
                    backgroundImage: `url(${session.concept_image.url})`,
                  }}
                >
                  {/* 深色遮罩 */}
                  <div className="absolute inset-0 bg-black/40 group-hover:bg-black/30 transition-all duration-300" />
                </div>
              )}

              {/* 内容区域 */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center text-white px-8 max-w-4xl">
                  {/* 标题 */}
                  <h1 className="text-4xl md:text-6xl font-bold mb-6 drop-shadow-2xl">
                    {session.title}
                  </h1>

                  {/* 描述 */}
                  {session.user_input && (
                    <p className="text-lg md:text-xl text-white/90 mb-8 line-clamp-3 drop-shadow-lg">
                      {session.user_input}
                    </p>
                  )}

                  {/* 标签 */}
                  <div className="flex items-center justify-center gap-4 text-sm">
                    {session.analysis_mode === "deep_thinking" && (
                      <span className="bg-purple-500/80 px-4 py-2 rounded-full backdrop-blur-sm">
                        深度思考模式
                      </span>
                    )}
                    <span className="bg-blue-500/80 px-4 py-2 rounded-full backdrop-blur-sm">
                      {new Date(session.created_at).toLocaleDateString("zh-CN")}
                    </span>
                  </div>

                  {/* 点击提示 */}
                  <div className="mt-8 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <p className="text-white/80 text-sm">
                      点击查看完整报告 →
                    </p>
                  </div>
                </div>
              </div>

              {/* 幻灯片编号 */}
              <div className="absolute bottom-8 left-8 text-white/60 text-sm">
                {index + 1} / {sessions.length}
              </div>
            </div>
          </SwiperSlide>
        ))}
      </Swiper>

      {/* 自定义分页器样式 */}
      <style jsx global>{`
        .swiper-pagination {
          bottom: 30px !important;
        }
        .swiper-pagination-bullet {
          width: 12px;
          height: 12px;
          background: white;
          opacity: 0.5;
        }
        .swiper-pagination-bullet-active {
          opacity: 1;
          background: white;
        }
        .swiper-button-prev,
        .swiper-button-next {
          color: white;
          background: rgba(0, 0, 0, 0.3);
          width: 50px;
          height: 50px;
          border-radius: 50%;
        }
        .swiper-button-prev:after,
        .swiper-button-next:after {
          font-size: 24px;
        }
      `}</style>
    </div>
  );
}
