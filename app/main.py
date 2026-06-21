from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models

from app.auth.router import router as auth_router
from app.brands.router import router as brand_router
from app.common.responses import error_response, success_response
from app.config import settings
from app.dashboard.router import router as dashboard_router
from app.files.router import router as files_router
from app.lookup.router import router as lookup_router
from app.parts.router import router as parts_router
from app.processing.router import router as processing_router


app = FastAPI(
    title=settings.APP_NAME,
    description="SpareTrack - Laptop Spare Parts Inventory Management System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://spare-track-fe.vercel.app",
        "https://spare-track-fe-qgnt.vercel.app",
        "https://tracker-tool.ghazatech.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_response(
            message="Internal server error",
            errors={"detail": str(exc)} if settings.DEBUG else {},
        ),
    )


app.include_router(auth_router)
app.include_router(brand_router)
app.include_router(files_router)
app.include_router(lookup_router)
app.include_router(parts_router)
app.include_router(processing_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return success_response(
        message="Welcome to SpareTrack API",
        data={
            "app_name": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "docs_url": "/docs",
        },
    )


@app.get("/health")
def health_check():
    return success_response(
        message="API is healthy",
        data={
            "status": "ok",
            "database": "configured",
            "lookup_provider": settings.LOOKUP_PROVIDER,
            "llm_model": settings.ANTHROPIC_MODEL,
            "search_provider": "tavily",
        },
    )