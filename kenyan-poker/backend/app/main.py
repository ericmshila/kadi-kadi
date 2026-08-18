from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.websocket import router as websocket_router


app = FastAPI(
    title="Kenyan Poker API",
    version="0.1.0",
)

# MVP: wide open for local development so the frontend dev server
# (different port/origin) can reach the API. Tighten this before
# deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(websocket_router)


@app.get("/")
def root():
    return {
        "name": "Kenyan Poker API",
        "status": "running",
    }