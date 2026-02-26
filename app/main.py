import asyncio
import sys

# I added this fix because standard asyncio loop on Windows has issues with Playwright and AsyncPG
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.api import endpoints
from app.routers import social_radar
from app.db.session import engine
from app.db.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # I verified here that database tables exist before starting the app
    print("Starting Lead Master...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables verified.")
    yield
    # I put this print here so we know when the app is fully stopped
    print("Shutting down...")

app = FastAPI(
    title="Lead Master B2B Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(social_radar.router, prefix="/api/v1/radar", tags=["Social Radar"])

# Include Routers
app.include_router(endpoints.router, prefix="/leads", tags=["Leads"])

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('app/static/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
