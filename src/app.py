from fastapi import FastAPI
from src.api.routes import router as github_router

app = FastAPI(
    title="BugTriage/Fix – Webhook API",
    version="0.1.0"
)
app.include_router(github_router, prefix="/webhooks")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
