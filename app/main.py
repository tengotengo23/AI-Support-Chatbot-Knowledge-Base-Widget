from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, db
from app.config import get_settings
from app.plans import PLANS
from app.routers import admin, auth, hooks, platform, widget
from app.services import telegram

log = logging.getLogger("app")
STATIC = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        db.configure(settings.database_url)
        db.init_db()
        poller = None
        if settings.telegram_bot_token and settings.telegram_mode != "off":
            try:
                if settings.telegram_mode == "webhook":
                    if not settings.telegram_webhook_secret:
                        raise telegram.TelegramError("TELEGRAM_WEBHOOK_SECRET is required for webhook mode")
                    telegram.setup_webhook(settings)
                else:
                    poller = telegram.Poller(settings)
                    poller.start()
            except telegram.TelegramError as exc:
                log.warning("Telegram disabled: %s", exc)
        log.info("%s %s started (LLM: %s, billing: %s)", settings.brand_name, __version__,
                 settings.llm_provider, settings.billing_enabled)
        yield
        if poller:
            poller.stop()

    app = FastAPI(title=settings.brand_name, version=__version__, lifespan=lifespan,
                  docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")

    @app.middleware("http")
    async def headers_and_cors(request: Request, call_next):
        is_widget_api = request.url.path.startswith("/api/widget/")
        if is_widget_api and request.method == "OPTIONS":
            response = Response(status_code=204)
        else:
            response = await call_next(request)
        if is_widget_api:
            # The widget runs on customers' websites. Per-workspace origin rules are enforced in
            # the endpoints; no cookies are ever used here.
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin") or "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "600"
            response.headers["Vary"] = "Origin"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.url.path.startswith(("/admin", "/api/auth", "/api/workspaces", "/api/platform")):
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    for r in (auth.router, admin.router, widget.router, hooks.router, platform.router):
        app.include_router(r)

    @app.get("/api/public/plans", tags=["public"])
    def public_plans():
        return {
            "billing_enabled": settings.billing_enabled,
            "platform_fee_percent": settings.platform_fee_percent,
            "plans": [p.public() for p in PLANS.values()],
        }

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"ok": True, "version": __version__}

    @app.get("/widget.js", include_in_schema=False)
    def widget_js():
        return FileResponse(
            STATIC / "widget.js",
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=300", "Access-Control-Allow-Origin": "*"},
        )

    @app.get("/admin", include_in_schema=False)
    def admin_page():
        return FileResponse(STATIC / "admin" / "index.html")

    @app.get("/demo", include_in_schema=False)
    def demo_page():
        return FileResponse(STATIC / "demo.html")

    @app.get("/", include_in_schema=False)
    def index():
        if not settings.landing_enabled:
            return RedirectResponse("/admin")
        return FileResponse(STATIC / "landing" / "index.html")

    @app.get("/legal", include_in_schema=False)
    def legal_page():
        return FileResponse(STATIC / "legal.html")

    def _redirect(target: str):
        def handler():
            return RedirectResponse(target)

        return handler

    for anchor in ("terms", "privacy", "refund"):
        app.add_api_route(f"/{anchor}", _redirect(f"/legal#{anchor}"), include_in_schema=False)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return FileResponse(STATIC / "favicon.svg", media_type="image/svg+xml")

    @app.get("/api/public/landing", tags=["public"])
    def landing_info():
        return {
            "brand_name": settings.brand_name,
            "demo_widget_key": settings.demo_widget_key,
            "public_url": settings.public_url,
            "badge_url": settings.badge_url,
            "legal_name": settings.legal_name,
            "contact_email": settings.contact_email,
            "legal_updated": settings.legal_updated,
        }

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
