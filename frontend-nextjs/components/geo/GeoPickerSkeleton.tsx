'use client';

/**
 * GeoPickerSkeleton — GeoPickerModal 的骨架屏
 * 在地图 JS 加载期间显示，避免空白闪烁
 */
export function GeoPickerSkeleton() {
  return (
    <div className="flex h-full w-full animate-pulse">
      {/* 左侧地图区 */}
      <div className="flex-1 bg-gray-200 rounded-l-xl" />
      {/* 右侧面板区 */}
      <div className="w-64 shrink-0 bg-white border-l border-gray-100 p-4 space-y-3 rounded-r-xl">
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-5/6" />
        <div className="mt-4 h-8 bg-gray-200 rounded-lg" />
      </div>
    </div>
  );
}
