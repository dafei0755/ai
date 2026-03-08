"""
分析路由模块 - 聚合器 (MT-11 拆分后)

子路由文件:
  _start_routes.py      POST /api/analysis/start
                        POST /api/analysis/start-with-files
                        POST /api/analysis/{id}/visual-reference/describe
  _lifecycle_routes.py  GET  /api/analysis/status/{session_id}
                        POST /api/analysis/resume
                        POST /api/analysis/followup
  _report_routes.py     GET  /api/analysis/result/{session_id}
                        GET  /api/analysis/report/{session_id}
                        GET  /api/analysis/report/{session_id}/download-pdf
                        GET  /api/analysis/report/{session_id}/download-all-experts-pdf
"""
from __future__ import annotations

from fastapi import APIRouter

from ._start_routes import router as _router_start
from ._lifecycle_routes import router as _router_lifecycle
from ._report_routes import router as _router_report

router = APIRouter(tags=["analysis"])
router.include_router(_router_start)
router.include_router(_router_lifecycle)
router.include_router(_router_report)
