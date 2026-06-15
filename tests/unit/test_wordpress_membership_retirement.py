from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def runtime_text(paths: list[str]) -> str:
    chunks: list[str] = []
    for path in paths:
        target = ROOT / path
        if target.exists():
            chunks.append(target.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def test_backend_no_longer_registers_wordpress_or_wpcom_routes() -> None:
    server = read("intelligent_project_analyzer/api/server.py")

    forbidden_markers = [
        "wordpress_jwt_service",
        "auth_routes",
        "member_routes",
        "wpcom_member_api",
        "WordPress JWT 认证路由已注册",
        "WPCOM Member 会员信息路由已注册",
        "WORDPRESS_URL",
        "WPCOM",
        "/api/member",
    ]

    for marker in forbidden_markers:
        assert marker not in server


def test_backend_wordpress_runtime_modules_are_retired() -> None:
    retired_paths = [
        "intelligent_project_analyzer/api/auth_routes.py",
        "intelligent_project_analyzer/api/member_routes.py",
        "intelligent_project_analyzer/api/wpcom_member_api.py",
        "intelligent_project_analyzer/api/auth_middleware.py",
        "intelligent_project_analyzer/services/wordpress_jwt_service.py",
    ]

    for path in retired_paths:
        assert not (ROOT / path).exists(), path


def test_search_routes_do_not_verify_with_wordpress_jwt() -> None:
    search_routes = read("intelligent_project_analyzer/api/search_routes.py")

    assert "wordpress_jwt_service" not in search_routes
    assert "get_jwt_service" not in search_routes
    assert "verify_token" not in search_routes


def test_frontend_runtime_no_longer_uses_wordpress_sso_or_wp_token_keys() -> None:
    frontend_paths = [
        *[str(path.relative_to(ROOT)) for path in (ROOT / "frontend-nextjs/app").rglob("*.tsx")],
        *[str(path.relative_to(ROOT)) for path in (ROOT / "frontend-nextjs/components").rglob("*.tsx")],
        *[str(path.relative_to(ROOT)) for path in (ROOT / "frontend-nextjs/contexts").rglob("*.tsx")],
        *[str(path.relative_to(ROOT)) for path in (ROOT / "frontend-nextjs/hooks").rglob("*.ts")],
        "frontend-nextjs/middleware.ts",
    ]
    text = runtime_text(frontend_paths)

    forbidden_markers = [
        "wp_jwt_token",
        "wp_jwt_user",
        "wp_jwt_token_timestamp",
        "wp-auth",
        "loginWithWordPress",
        "WordPress",
        "WPCOM",
        "www.ucppt.com/nextjs",
        "/api/member",
    ]

    for marker in forbidden_markers:
        assert marker not in text


def test_frontend_old_wordpress_auth_pages_are_retired() -> None:
    retired_paths = [
        "frontend-nextjs/app/auth/callback/page.tsx",
        "frontend-nextjs/app/auth/kicked/page.tsx",
        "frontend-nextjs/app/auth/login/manual/page.tsx",
    ]

    for path in retired_paths:
        assert not (ROOT / path).exists(), path


def test_wordpress_membership_card_and_hook_are_retired() -> None:
    retired_paths = [
        "frontend-nextjs/components/layout/MembershipCard.tsx",
        "frontend-nextjs/hooks/useMembership.ts",
        "frontend-nextjs/__tests__/MembershipCard.test.tsx",
        "frontend-nextjs/lib/wp-auth.ts",
    ]

    for path in retired_paths:
        assert not (ROOT / path).exists(), path
