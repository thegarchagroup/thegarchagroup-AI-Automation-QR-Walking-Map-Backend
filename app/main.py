from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers import auth, places, config as config_router

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


@app.get("/health")
def health():
    return {"status": "ok"}
