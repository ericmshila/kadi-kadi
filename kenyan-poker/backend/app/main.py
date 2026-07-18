from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="Kenyan Poker API",
    version="0.1.0",
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "Kenyan Poker API",
        "status": "running",
    }