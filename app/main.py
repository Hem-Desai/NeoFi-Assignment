from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import msgpack
from fastapi.responses import Response
from typing import Union
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.notifications import router as notifications_router
from app.core.config import settings
from app.core.exceptions import AppException

app = FastAPI(
    title="Collaborative Event Management System",
    description="RESTful API for an event scheduling application with collaborative editing features",
    version="1.0.0",
    docs_url=None,  
    redoc_url=None,  
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.middleware("http")
async def content_negotiation_middleware(request: Request, call_next):
    response = await call_next(request)
    
    accept = request.headers.get("Accept", "")
    
    if "application/msgpack" in accept and hasattr(response, "body"):
        try:
            body = response.body
            if isinstance(body, bytes):
                body = body.decode("utf-8")
            
            import json
            data = json.loads(body)
            
            packed = msgpack.packb(data)
            
            return Response(
                content=packed,
                media_type="application/msgpack",
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception:
            return response
    
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host

    client_ip = request.client.host
    
    # TODO: Implement rate limiting logic
    # For now, just pass through all requests
    
    response = await call_next(request)
    return response

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

# Include routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(events_router.router, prefix="/api/events", tags=["Events"])
app.include_router(notifications_router.router, prefix="/api/notifications", tags=["Notifications"])

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint to verify the API is running
    """
    return {
        "message": "Welcome to the Collaborative Event Management System API",
        "version": app.version,
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
