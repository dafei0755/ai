/**
 * useGeoStore — GeoAnchor + GeoThesis 全局状态
 *
 * G1-G4 层唯一地理真相源。GeoAnchorCard / GeoPickerModal / GeoCanvasView 均读写此 store。
 * G1: geoAnchor — 坐标锚点
 * G4: geoThesis — 地点商业命题（AI 生成，持久化）
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { GeoAnchor, GeoThesis } from '@/types/geo';

interface GeoState {
  /** G1: 当前项目的地理锚点，null 表示未设置 */
  geoAnchor: GeoAnchor | null;
  /** G4: 地点商业命题，由 AI 基于 G3 情报生成 */
  geoThesis: GeoThesis | null;
  /** 命题生成中的加载状态 */
  thesisLoading: boolean;
  /** 弹窗开关 */
  pickerOpen: boolean;
  /** 当前弹窗模式：'edit' = 选址/修改，'view' = 只读查看 */
  pickerMode: 'view' | 'edit';

  setGeoAnchor: (anchor: GeoAnchor) => void;
  clearGeoAnchor: () => void;
  setGeoThesis: (thesis: GeoThesis) => void;
  clearGeoThesis: () => void;
  setThesisLoading: (loading: boolean) => void;
  openPicker: () => void;
  openViewer: () => void;
  closePicker: () => void;
}

export const useGeoStore = create<GeoState>()(
  persist(
    (set) => ({
      geoAnchor: null,
      geoThesis: null,
      thesisLoading: false,
      pickerOpen: false,
      pickerMode: 'edit',

      setGeoAnchor: (anchor) => set({ geoAnchor: anchor, pickerOpen: false }),
      clearGeoAnchor: () => set({ geoAnchor: null, geoThesis: null }),
      setGeoThesis: (thesis) => set({ geoThesis: thesis, thesisLoading: false }),
      clearGeoThesis: () => set({ geoThesis: null }),
      setThesisLoading: (loading) => set({ thesisLoading: loading }),
      openPicker: () => set({ pickerOpen: true, pickerMode: 'edit' }),
      openViewer: () => set({ pickerOpen: true, pickerMode: 'view' }),
      closePicker: () => set({ pickerOpen: false }),
    }),
    {
      name: 'geo-anchor-storage',
      // 持久化 geoAnchor 和 geoThesis，弹窗/加载状态不持久化
      partialize: (state) => ({ geoAnchor: state.geoAnchor, geoThesis: state.geoThesis }),
    },
  ),
);
