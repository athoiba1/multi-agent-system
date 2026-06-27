from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="Multi-Agent Orchestration System",
    description="A system that decomposes complex tasks into discrete steps and executes them using specialized agents",
    version="1.0.0",
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
