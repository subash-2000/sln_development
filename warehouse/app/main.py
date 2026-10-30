from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger, setup_logging
from app.core.middleware import RequestIDMiddleware, TimingAndLoggingMiddleware
from app.core.response import error_response, success_response
import app.core.audit  # noqa: F401 - Register SQLAlchemy before_flush audit hook
from app.modules.audit.router import router as audit_router
from app.modules.billing import billing_router
from app.modules.branches.router import router as branches_router
from app.modules.companies.router import router as companies_router
from app.modules.customers.router import router as customers_router
from app.modules.inventory.router import router as inventory_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.invoicing import invoicing_router
from app.modules.jobwork.router import router as jobwork_router
from app.modules.locations.router import router as locations_router
from app.modules.logistics.router import router as logistics_router
from app.modules.migration.router import router as migration_router
from app.modules.products.router import router as products_router
from app.modules.rate_cards.router import router as rate_cards_router
from app.modules.returns import returns_router
from app.modules.rings import rings_router
from app.modules.reports.router import router as reports_router
from app.modules.roles.router import router as roles_router
from app.modules.sequences.router import router as sequences_router
from app.modules.stocktake.router import router as stocktake_router
from app.modules.transport.router import router as transport_router
from app.modules.users.router import router as users_router
from app.modules.vendor_stock.router import router as vendor_stock_router
from app.modules.vendors.router import router as vendors_router
from app.modules.warehouses.router import router as warehouses_router

# Initialize logger
setup_logging()

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Enterprise Modular Monolith Backend for SLN Warehouse Management System (WMS).",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Mount Middlewares
# 2. Request ID Correlation Middleware
app.add_middleware(RequestIDMiddleware)

# 3. Timing and Logging Middleware
app.add_middleware(TimingAndLoggingMiddleware)

# 1. CORS (Outermost - handle preflight early)
# MUST BE ADDED LAST TO BE EXECUTED FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id or ""},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    field_errors = []
    for err in exc.errors():
        field_errors.append(
            {
                "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg"),
                "type": err.get("type"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            message="Request validation failed",
            error_code="VALIDATION_ERROR",
            details={"errors": field_errors},
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id or ""},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
            error_code="HTTP_ERROR",
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id or ""},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(f"Unhandled server exception occurred: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            message="An unexpected server error occurred. Please contact system administration.",
            error_code="INTERNAL_SERVER_ERROR",
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id or ""},
    )


# System Health Endpoints
@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Verifies application availability and runtime environment status."""
    return success_response(
        data={
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        message="Service is operational",
    )


@app.get("/api/v1/ping", tags=["System"])
async def ping() -> dict:
    """Lightweight ping probe for API v1."""
    return success_response(
        data={"ping": "pong"},
        message="Pong",
    )


# Mount API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(sequences_router, prefix="/api/v1")
app.include_router(companies_router, prefix="/api/v1")
app.include_router(branches_router, prefix="/api/v1")
app.include_router(vendors_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(transport_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(rate_cards_router, prefix="/api/v1")
app.include_router(warehouses_router, prefix="/api/v1")
app.include_router(locations_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(vendor_stock_router, prefix="/api/v1")
app.include_router(jobwork_router, prefix="/api/v1")
app.include_router(logistics_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(invoicing_router, prefix="/api/v1")
app.include_router(returns_router, prefix="/api/v1")
app.include_router(rings_router, prefix="/api/v1")
app.include_router(stocktake_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(migration_router, prefix="/api/v1")
