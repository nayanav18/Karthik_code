from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.auth import FirebaseAuthMiddleware
from app.routers import dashboards, folders

app = FastAPI(title="Ireland Constellation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server; tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth runs before permission checks on every non-public route.
app.add_middleware(FirebaseAuthMiddleware)

app.include_router(dashboards.router)
app.include_router(folders.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
