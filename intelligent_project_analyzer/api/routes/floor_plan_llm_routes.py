# -*- coding: utf-8 -*-
"""
平面图 LLM 语义骨架识别路由

Layer 3 两阶段流水线的 Phase 1：
  - 接受 PDF 文件引用 + 空间区域上下文
  - 将 PDF 第一页渲染为图像
  - 调用 Vision LLM 提取几何语义骨架（墙线、门洞、柱子、比例估算）
  - 返回结构化 JSON 供 trace route.ts 的 Phase 2 几何分析使用
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/floor-plan", tags=["平面图 LLM 识别"])

# ─── 上传目录（与 Next.js trace route.ts 的 UPLOAD_DIR 对齐）───────────────────
# Next.js: path.join(process.cwd(), '.uploads', 'plan-drawings')
# Python 服务从环境变量读取，默认与 Next.js 同级目录
_DEFAULT_UPLOAD_DIR = str(
    Path(__file__).parent.parent.parent.parent / "frontend-nextjs" / ".uploads" / "plan-drawings"
)
UPLOAD_DIR = Path(os.getenv("PLAN_DRAWINGS_UPLOAD_DIR", _DEFAULT_UPLOAD_DIR))


# ─── Pydantic 模型 ─────────────────────────────────────────────────────────────


class LLMSkeletonRequest(BaseModel):
    """LLM 语义骨架识别请求"""

    fileUrl: str = Field(..., description="已上传的 PDF 文件 URL（与 trace route 同格式）")
    spatialZone: str = Field(default="建筑平面图", description="空间区域描述（如 酒店客房/公寓/办公室）")
    pageIndex: int = Field(default=0, description="PDF 页码（0-based）")
    renderDpi: int = Field(default=150, description="渲染 DPI（越高精度越好但越慢）")


class WallSegmentHint(BaseModel):
    """LLM 估算的墙线提示（归一化坐标 0-1）"""

    x1: float
    y1: float
    x2: float
    y2: float
    thickness_mm: Optional[float] = None  # 估算厚度（mm）
    wall_type: Optional[str] = None  # exterior / interior / partition


class OpeningHint(BaseModel):
    """门窗洞口提示"""

    type: str  # door / window
    x: float  # 中心归一化 x
    y: float  # 中心归一化 y
    width_mm: Optional[float] = None
    wall_direction: Optional[str] = None  # horizontal / vertical


class ColumnHint(BaseModel):
    """结构柱提示"""

    cx: float
    cy: float
    width_mm: Optional[float] = None
    depth_mm: Optional[float] = None


class ScaleHint(BaseModel):
    """比例估算提示"""

    mm_per_normalized: Optional[float] = Field(
        None, description="每归一化单位对应多少毫米（基于 LLM 估算）"
    )
    typical_room_width_mm: Optional[float] = None
    typical_wall_thickness_mm: Optional[float] = None
    confidence: str = "low"  # low / medium / high


class LLMSkeletonResponse(BaseModel):
    """LLM 语义骨架识别响应"""

    status: str  # success / error / no_vision_llm
    spatial_zone: str
    walls: List[WallSegmentHint] = []
    openings: List[OpeningHint] = []
    columns: List[ColumnHint] = []
    scale_hint: Optional[ScaleHint] = None
    raw_llm_output: Optional[str] = None
    error: Optional[str] = None


# ─── LLM 几何骨架提示词 ────────────────────────────────────────────────────────


def _build_skeleton_prompt(spatial_zone: str) -> str:
    """
    构建专用于几何骨架提取的 Vision LLM 提示词。
    与 file_processor._get_floor_plan_prompt() 的高层描述不同，
    本提示词要求 LLM 输出归一化坐标系下的精确几何位置。
    """
    return f"""你是一位建筑 CAD 图纸分析专家。请分析这张平面图，输出精确的几何骨架数据。
空间类型：{spatial_zone}

**坐标系说明**：
- 图像左上角为 (0, 0)，右下角为 (1, 1)
- x 向右增加，y 向下增加
- 所有坐标均为 0-1 之间的归一化小数

**请输出以下 JSON 格式（只输出 JSON，不要其他文字）**：
{{
  "walls": [
    {{
      "x1": 0.05, "y1": 0.10, "x2": 0.95, "y2": 0.10,
      "thickness_mm": 200,
      "wall_type": "exterior"
    }}
  ],
  "openings": [
    {{
      "type": "door",
      "x": 0.30, "y": 0.10,
      "width_mm": 900,
      "wall_direction": "horizontal"
    }},
    {{
      "type": "window",
      "x": 0.70, "y": 0.10,
      "width_mm": 1800,
      "wall_direction": "horizontal"
    }}
  ],
  "columns": [
    {{
      "cx": 0.12, "cy": 0.15,
      "width_mm": 600,
      "depth_mm": 600
    }}
  ],
  "scale_hint": {{
    "typical_room_width_mm": 3600,
    "typical_wall_thickness_mm": 200,
    "confidence": "medium"
  }}
}}

**识别要求**：
1. walls：识别所有**结构墙体**的中心线（外墙、内墙、隔断），用直线段表示中心线
   - 外墙(exterior)：建筑外围，厚度通常 200-400mm
   - 内墙(interior)：分隔主要空间，厚度通常 120-200mm
   - 隔断(partition)：轻质隔墙，厚度通常 100mm 以下
   - 优先输出水平和垂直的墙线（偏斜墙也要输出）
   - 最多输出 60 条最重要的墙线
   - ⚠️ **重要：不要输出装修完成面线**——完成面线是紧贴结构墙外侧、间距 20-60mm 的细线，
     代表抹灰/饰面层厚度，不是独立的墙体，请忽略它们，只输出结构墙中心线
   - ⚠️ **不要输出幕墙玻璃格线**——幕墙玻璃分格线（竖向等间距细线）不是墙，请忽略
   - ⚠️ **门窗洞口处的墙体请在洞口两侧分别输出**——门洞/窗洞使墙体中断，
     洞口两侧的墙段应作为独立线段各自输出，不要试图画一条穿越洞口的完整线
2. openings：识别所有门洞和窗洞的中心位置
   - door：带门扇弧线符号，宽度通常 800-1500mm
   - window：窗洞，宽度通常 600-3600mm
   - 最多输出 30 个
3. columns：识别结构柱（通常为矩形或方形实心填充区域）
   - 最多输出 20 个
4. scale_hint：根据尺寸标注或典型建筑知识估算比例
   - 如图上有尺寸数字，优先使用数字
   - 若为酒店客房，典型开间 3600-4200mm；若为公寓，通常 3000-4500mm
   - confidence: "high"（有明确尺寸标注）/"medium"（参考典型值）/"low"（无法确定）

**注意**：
- 坐标必须是 0-1 之间的小数，精确到小数点后 3 位
- mm 值是真实物理尺寸估算
- 如果看不清楚，宁可少输出，不要乱猜坐标
- 只输出结构墙的中心线，不要输出装修完成面线（饰面线）、幕墙玻璃格线、家具轮廓线
- 只输出 JSON，不要输出任何解释文字"""


# ─── PDF 工具 ─────────────────────────────────────────────────────────────────


def _render_pdf_page_to_jpeg(pdf_path: Path, page_index: int = 0, dpi: int = 150) -> bytes:
    """将 PDF 指定页面渲染为 JPEG bytes（位图兜底路径）"""
    from pdf2image import convert_from_path

    images = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=page_index + 1,
        last_page=page_index + 1,
        fmt="jpeg",
    )
    if not images:
        raise ValueError(f"PDF 渲染失败：无法渲染页 {page_index}")
    img = images[0]

    # 压缩到合理尺寸（长边不超过 4096px），节省 LLM token
    max_side = 4096
    if max(img.size) > max_side:
        ratio = max_side / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _extract_pdf_vector_geometry(
    pdf_path: Path,
    page_index: int = 0,
    max_lines: int = 600,
    max_rects: int = 200,
) -> Dict[str, Any]:
    """
    使用 pdfplumber 直接提取 PDF 矢量几何对象（线段、矩形、曲线），
    归一化到 0-1 坐标系（左上角原点，x 向右，y 向下）。

    返回 dict::

        {
            'page_size_pt': [W, H],
            'lines': [...],       # 线段列表
            'rects': [...],       # 矩形列表
            'curves': [...],      # 曲线端点列表
            'total_raw_lines': N, # 原始线段总数（降采样前）
        }
    """
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_index]
        W = float(page.width)
        H = float(page.height)

        def nx(x: float) -> float:
            return round(float(x) / W, 4)

        def ny(y: float) -> float:
            # PDF 坐标系：原点在左下角，y 向上 → 翻转为左上角原点 y 向下
            return round(1.0 - float(y) / H, 4)

        # ── 线段 ──────────────────────────────────────────────────────────────
        raw_lines = page.lines or []
        lines: List[Dict[str, Any]] = []
        for obj in raw_lines:
            lw = round(float(obj.get("linewidth") or obj.get("width") or 1), 2)
            x1, y1 = nx(obj["x0"]), ny(obj["y0"])
            x2, y2 = nx(obj["x1"]), ny(obj["y1"])
            if abs(x2 - x1) < 0.0002 and abs(y2 - y1) < 0.0002:
                continue  # 零长度线过滤
            lines.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "lw": lw})

        total_raw_lines = len(lines)
        # 线段过多时按线宽降序截取（优先保留粗线/结构线）
        if len(lines) > max_lines:
            lines.sort(key=lambda s: -s["lw"])
            lines = lines[:max_lines]

        # ── 矩形 ──────────────────────────────────────────────────────────────
        raw_rects = page.rects or []
        rects: List[Dict[str, Any]] = []
        for obj in raw_rects:
            # PDF y1 < y2（底部 < 顶部），翻转后 y1_flipped 是矩形顶端
            x = nx(obj["x0"])
            y = ny(obj["y1"])  # ny(y1_pdf) = 1 - y1_pdf/H = 上边（翻转后）
            w = round(abs(nx(obj["x1"]) - nx(obj["x0"])), 4)
            h = round(abs(ny(obj["y0"]) - ny(obj["y1"])), 4)
            if w < 0.001 or h < 0.001:
                continue
            fill = obj.get("fill") or obj.get("non_stroking_color")
            rects.append({"x": x, "y": y, "w": w, "h": h, "filled": bool(fill)})
            if len(rects) >= max_rects:
                break

        # ── 曲线（门弧等） ─────────────────────────────────────────────────────
        raw_curves = page.curves or []
        curves: List[Dict[str, Any]] = []
        for obj in raw_curves[:80]:
            pts = obj.get("pts", [])
            if pts and len(pts) >= 2:
                curves.append({
                    "x0": nx(pts[0][0]), "y0": ny(pts[0][1]),
                    "x1": nx(pts[-1][0]), "y1": ny(pts[-1][1]),
                })

        return {
            "page_size_pt": [round(W, 1), round(H, 1)],
            "lines": lines,
            "rects": rects,
            "curves": curves,
            "total_raw_lines": total_raw_lines,
        }


def _build_skeleton_prompt_from_vectors(spatial_zone: str, geo: Dict[str, Any]) -> str:
    """基于矢量几何数据构建纯文本 LLM 提示词（不依赖图像）。"""
    lines_json = json.dumps(geo["lines"], separators=(",", ":"))
    rects_json = json.dumps(geo["rects"], separators=(",", ":"))
    curves_json = json.dumps(geo["curves"], separators=(",", ":"))

    return f"""你是建筑 CAD 图纸分析专家。以下是从矢量 PDF 直接提取的几何对象原始数据（精度无损）。
坐标系：左上角 (0,0)，右下角 (1,1)，x 向右，y 向下（已归一化）。
空间类型：{spatial_zone}
页面尺寸（pt）：{geo['page_size_pt']}（原始线段总数：{geo['total_raw_lines']}）

**线段 lines**（{len(geo['lines'])} 条，格式 {{x1,y1,x2,y2,lw=线宽pt}}）：
{lines_json}

**矩形 rects**（{len(geo['rects'])} 个，格式 {{x,y=左上角,w,h,filled=是否填充}}）：
{rects_json}

**曲线端点 curves**（{len(geo['curves'])} 段）：
{curves_json}

---
请根据以上原始矢量数据识别建筑语义骨架，**只输出 JSON，不要任何其他文字**：
{{
  "walls": [
    {{"x1":0.05,"y1":0.10,"x2":0.95,"y2":0.10,"thickness_mm":200,"wall_type":"exterior"}}
  ],
  "openings": [
    {{"type":"door","x":0.30,"y":0.10,"width_mm":900,"wall_direction":"horizontal"}},
    {{"type":"window","x":0.70,"y":0.10,"width_mm":1800,"wall_direction":"horizontal"}}
  ],
  "columns": [
    {{"cx":0.12,"cy":0.15,"width_mm":600,"depth_mm":600}}
  ],
  "scale_hint": {{
    "typical_room_width_mm":3600,
    "typical_wall_thickness_mm":200,
    "confidence":"medium"
  }}
}}

识别规则：
- walls：成对平行线（间距≈墙厚 100-400mm）→ 取中心线；filled 且细长的 rect → 填充墙；最多 60 条
  - exterior 外墙（lw 粗、处于边缘）；interior 内墙；partition 隔断（lw 细）
  - 不输出装修完成面线（紧贴结构墙外侧 20-60mm 的伴随线）
  - 门窗洞口处在缺口两侧分别输出墙段
- openings：墙线缺口 + 附近 curve → door；缺口无 curve → window；最多 30 个
- columns：filled=true 且近似方形/矩形的 rect → 结构柱；最多 20 个
- scale_hint：有尺寸标注数字时使用，否则按空间类型典型值估算
  - confidence: high（有标注）/ medium（推断）/ low（无依据）
- 坐标精确到小数点后 3 位，mm 值为真实物理尺寸估算"""


# ─── LLM JSON 解析工具 ────────────────────────────────────────────────────────


def _parse_llm_skeleton(raw: str) -> Dict[str, Any]:
    """从 LLM 输出中提取并解析 JSON skeleton"""
    # 先尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 块
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取第一个 { ... } 块
    match = re.search(r"\{[\s\S]+\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def _clamp01(v: Any) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def _safe_float(v: Any) -> Optional[float]:
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _build_response_from_parsed(parsed: Dict[str, Any], spatial_zone: str, raw: str) -> LLMSkeletonResponse:
    """从解析后的 dict 构建 LLMSkeletonResponse"""
    walls: List[WallSegmentHint] = []
    for w in parsed.get("walls", [])[:60]:
        if not isinstance(w, dict):
            continue
        try:
            walls.append(
                WallSegmentHint(
                    x1=_clamp01(w.get("x1", 0)),
                    y1=_clamp01(w.get("y1", 0)),
                    x2=_clamp01(w.get("x2", 0)),
                    y2=_clamp01(w.get("y2", 0)),
                    thickness_mm=_safe_float(w.get("thickness_mm")),
                    wall_type=w.get("wall_type"),
                )
            )
        except Exception:
            continue

    openings: List[OpeningHint] = []
    for o in parsed.get("openings", [])[:30]:
        if not isinstance(o, dict):
            continue
        try:
            openings.append(
                OpeningHint(
                    type=str(o.get("type", "door")),
                    x=_clamp01(o.get("x", 0)),
                    y=_clamp01(o.get("y", 0)),
                    width_mm=_safe_float(o.get("width_mm")),
                    wall_direction=o.get("wall_direction"),
                )
            )
        except Exception:
            continue

    columns: List[ColumnHint] = []
    for c in parsed.get("columns", [])[:20]:
        if not isinstance(c, dict):
            continue
        try:
            columns.append(
                ColumnHint(
                    cx=_clamp01(c.get("cx", 0)),
                    cy=_clamp01(c.get("cy", 0)),
                    width_mm=_safe_float(c.get("width_mm")),
                    depth_mm=_safe_float(c.get("depth_mm")),
                )
            )
        except Exception:
            continue

    scale_hint: Optional[ScaleHint] = None
    sh = parsed.get("scale_hint")
    if isinstance(sh, dict):
        room_w = _safe_float(sh.get("typical_room_width_mm"))
        wall_t = _safe_float(sh.get("typical_wall_thickness_mm"))
        confidence = sh.get("confidence", "low")
        if confidence not in ("low", "medium", "high"):
            confidence = "low"

        # 若 walls 中有厚度信息，可用于推算 mm_per_normalized
        # （归一化坐标系宽度 = 1.0 对应真实尺寸需要从其他信息推断）
        mm_per_norm: Optional[float] = _safe_float(sh.get("mm_per_normalized"))

        scale_hint = ScaleHint(
            mm_per_normalized=mm_per_norm,
            typical_room_width_mm=room_w,
            typical_wall_thickness_mm=wall_t,
            confidence=confidence,
        )

    return LLMSkeletonResponse(
        status="success",
        spatial_zone=spatial_zone,
        walls=walls,
        openings=openings,
        columns=columns,
        scale_hint=scale_hint,
        raw_llm_output=raw[:2000] if raw else None,  # 截断，避免响应过大
    )


# ─── 安全文件名提取（与 route.ts getSafeFileName 对齐）─────────────────────────


def _get_safe_filename(file_url: str) -> str:
    """从 fileUrl 中提取安全文件名（与 Next.js 侧逻辑对齐）"""
    from urllib.parse import urlparse, unquote

    parsed = urlparse(file_url)
    # 取路径最后一段
    raw_name = Path(unquote(parsed.path)).name
    if not raw_name:
        raise ValueError("无法从 fileUrl 提取文件名")
    # 过滤危险字符（与 route.ts getSafeFileName 对齐）
    safe = re.sub(r"[^a-zA-Z0-9._\-]", "_", raw_name)
    if not safe:
        raise ValueError(f"非法文件名: {raw_name}")
    return safe


# ─── 主端点 ────────────────────────────────────────────────────────────────────


@router.post("/llm-skeleton", response_model=LLMSkeletonResponse)
async def floor_plan_llm_skeleton(request: LLMSkeletonRequest) -> LLMSkeletonResponse:
    """
    **平面图 LLM 语义骨架识别**

    Phase 1 两阶段流水线：
    1. 优先用 pdfplumber 直接提取矢量几何数据（无精度损失）
    2. 构建纯文本提示词调用文本 LLM（更快、更便宜、更准确）
    3. 若矢量提取失败（扫描件/图像嵌入 PDF），自动降级为位图路径（Vision LLM）
    4. 返回结构化 JSON 供 trace route.ts 的 Phase 2 几何分析使用
    """
    # ── 1. 导入 LLM 全局实例 ──────────────────────────────────────────────────
    try:
        from intelligent_project_analyzer.services.file_processor import file_processor

        vision_llm = file_processor.vision_llm
        # 文本 LLM 优先（矢量路径不需要视觉模型，更便宜）
        text_llm = getattr(file_processor, "llm", None) or vision_llm
    except Exception as e:
        logger.warning(f"⚠️ [llm-skeleton] 无法加载 file_processor: {e}")
        vision_llm = None
        text_llm = None

    if vision_llm is None and text_llm is None:
        return LLMSkeletonResponse(
            status="no_vision_llm",
            spatial_zone=request.spatialZone,
            error="Vision LLM 未初始化，请检查 VISION_PROVIDER 和 API Key 配置",
        )

    # ── 2. 解析文件路径 ────────────────────────────────────────────────────────
    try:
        safe_name = _get_safe_filename(request.fileUrl)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = Path(safe_name).suffix.lower()
    if ext not in (".pdf",):
        raise HTTPException(
            status_code=400,
            detail=f"LLM 骨架识别仅支持 PDF 文件，当前格式: {ext}",
        )

    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件未找到: {safe_name}")

    # ── 3. 优先路径：pdfplumber 矢量提取 → 文本 LLM ──────────────────────────
    use_vector_path = False
    message = None

    try:
        geo = await asyncio.to_thread(
            _extract_pdf_vector_geometry,
            file_path,
            request.pageIndex,
        )
        n_lines = len(geo["lines"])
        n_rects = len(geo["rects"])
        logger.info(
            f"📐 [llm-skeleton] 矢量提取: lines={n_lines}({geo['total_raw_lines']} raw)"
            f" rects={n_rects} curves={len(geo['curves'])}"
        )
        # 矢量数据充分时走文本路径；不足 15 条线认为是扫描件，降级位图路径
        if n_lines >= 15 or n_rects >= 5:
            use_vector_path = True
            from langchain_core.messages import HumanMessage
            prompt_text = _build_skeleton_prompt_from_vectors(request.spatialZone, geo)
            message = HumanMessage(content=prompt_text)
            logger.info(f"✅ [llm-skeleton] 使用矢量文本路径，prompt 长度={len(prompt_text)}")
        else:
            logger.info(
                f"⚠️ [llm-skeleton] 矢量数据不足（lines={n_lines}），降级为位图路径"
            )
    except Exception as e:
        logger.warning(f"⚠️ [llm-skeleton] pdfplumber 提取失败: {e}，降级为位图路径")

    # ── 4. 降级路径：渲染为 JPEG → Vision LLM ────────────────────────────────
    if not use_vector_path:
        if vision_llm is None:
            return LLMSkeletonResponse(
                status="no_vision_llm",
                spatial_zone=request.spatialZone,
                error="矢量提取失败且 Vision LLM 未初始化，无法处理此 PDF",
            )
        try:
            jpeg_bytes = await asyncio.to_thread(
                _render_pdf_page_to_jpeg,
                file_path,
                request.pageIndex,
                request.renderDpi,
            )
        except Exception as e:
            logger.error(f"❌ [llm-skeleton] PDF 渲染失败: {e}")
            raise HTTPException(status_code=500, detail=f"PDF 渲染失败: {e}")

        image_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        logger.info(f"🖼️ [llm-skeleton] 位图降级: {safe_name}, 大小={len(jpeg_bytes)//1024}KB")
        from langchain_core.messages import HumanMessage
        prompt_text = _build_skeleton_prompt(request.spatialZone)
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
            ]
        )

    # ── 5. 调用 LLM（矢量路径用 text_llm，位图路径用 vision_llm）──────────────
    active_llm = text_llm if use_vector_path else vision_llm
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(active_llm.invoke, [message]),
            timeout=60.0,
        )
        raw_content: str = response.content or ""
        logger.info(
            f"✅ [llm-skeleton] LLM 响应: {len(raw_content)} 字符"
            f"（{'矢量文本' if use_vector_path else '位图视觉'}路径）"
        )
    except asyncio.TimeoutError:
        logger.error("❌ [llm-skeleton] LLM 调用超时（60s）")
        raise HTTPException(status_code=504, detail="LLM 调用超时，请稍后重试")
    except Exception as e:
        logger.error(f"❌ [llm-skeleton] LLM 调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {e}")

    # ── 6. 解析 JSON 骨架 ──────────────────────────────────────────────────────
    parsed = _parse_llm_skeleton(raw_content)
    if not parsed:
        logger.warning(f"⚠️ [llm-skeleton] LLM 未返回有效 JSON: {raw_content[:200]}")
        return LLMSkeletonResponse(
            status="error",
            spatial_zone=request.spatialZone,
            error="LLM 未返回有效 JSON 骨架",
            raw_llm_output=raw_content[:500],
        )

    result = _build_response_from_parsed(parsed, request.spatialZone, raw_content)
    logger.info(
        f"✅ [llm-skeleton] 骨架提取完成: walls={len(result.walls)}, "
        f"openings={len(result.openings)}, columns={len(result.columns)}"
    )
    return result
