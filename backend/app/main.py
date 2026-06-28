"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers.stock import router as stock_router
from app.routers.invest import router as invest_router
from app.routers.practical_select import router as practical_select_router
from app.routers.notif import router as notif_router
from app.routers.collect import router as collect_router
from app.tasks.scheduler import setup_scheduler, scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready.")
    setup_scheduler()
    logger.info("Scheduler started.")
    yield
    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Shutting down...")


app = FastAPI(
    title="投资助手 API",
    description="股票财务分析 & 龙江投资平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Vue dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(stock_router)
app.include_router(invest_router)
app.include_router(practical_select_router)
app.include_router(notif_router)
app.include_router(collect_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "投资助手"}
