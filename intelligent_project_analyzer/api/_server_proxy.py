"""
单例延迟代理 — 消除 api 子模块的重复 _ServerProxy 定义
======================================================

问题背景：
  server.py 在启动时 import 各路由模块，而路由模块又需要访问
  server.py 中的运行时对象（session_manager / broadcast_to_websockets 等），
  直接 import 会形成循环依赖。

解决方案：
  将 _ServerProxy 提取为唯一实现，各路由模块改为：

      from intelligent_project_analyzer.api._server_proxy import server_proxy as _server

  这样模块级 import 链不再触达 server.py，首次访问属性时才真正导入。
"""
from __future__ import annotations

__all__ = ["server_proxy"]


class _ServerProxy:
    """惰性代理：首次访问任意属性时才导入 api.server 模块。"""

    __slots__ = ()

    def __getattr__(self, name: str):  # noqa: ANN204
        import intelligent_project_analyzer.api.server as _srv  # noqa: PLC0415

        return getattr(_srv, name)


#: 全局单例——各路由模块直接导入此实例，勿自行实例化 _ServerProxy
server_proxy = _ServerProxy()
