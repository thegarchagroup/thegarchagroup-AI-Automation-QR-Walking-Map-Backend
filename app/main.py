from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routers import auth, places, config as config_router, uploads

settings = get_settings()

# Creates tables if they don't exist yet. Fine for this project's size;
# a bigger app would use Alembic migrations instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WalkGuide API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(places.router)
app.include_router(config_router.router)
app.include_router(uploads.router)

# Serves whatever's saved by the /uploads POST route back out as plain
# static files — e.g. a photo saved as uploads/abc123.jpg is reachable at
# GET /uploads/abc123.jpg (and, behind your reverse proxy, at
# https://yourdomain.com/walk-map-api/uploads/abc123.jpg).
app.mount("/uploads", StaticFiles(directory=uploads.UPLOAD_DIR), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}