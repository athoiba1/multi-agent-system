from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
from agents.planner import PlannerAgent
from agents.retriever import RetrieverAgent
from agents.analyzer import AnalyzerAgent
from agents.writer import WriterAgent
from orchestrator.decomposer import Decomposer
from orchestrator.pipeline import Pipeline
from orchestrator.batcher import BatchProcessor
from streaming.events import EventQueue, Event, EventType
from streaming.handler import WebSocketManager
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["pipeline"])

event_queue = EventQueue()
ws_manager = WebSocketManager()


def create_agents(simulate_failure: bool = False):
    return {
        "planner": PlannerAgent(event_queue=event_queue),
        "retriever": RetrieverAgent(event_queue=event_queue, simulate_failure=simulate_failure),
        "analyzer": AnalyzerAgent(event_queue=event_queue),
        "writer": WriterAgent(event_queue=event_queue),
    }


class TaskRequest(BaseModel):
    task: str
    simulate_failure: bool = False


class BatchTaskRequest(BaseModel):
    tasks: list[str]
    batch_size: int = 5


@router.post("/execute")
async def execute_task(request: TaskRequest):
    agents = create_agents(simulate_failure=request.simulate_failure)
    decomposer = Decomposer(planner_agent=agents["planner"], event_queue=event_queue)
    pipeline = Pipeline(agents=agents, event_queue=event_queue)

    task = await decomposer.decompose(request.task)
    result = await pipeline.execute(task)

    return {
        "task_id": result.task_id,
        "status": result.status.value,
        "steps": [
            {
                "name": sr.step_name,
                "status": sr.status.value,
                "duration_ms": sr.duration_ms,
            }
            for sr in result.steps_results
        ],
        "final_output": result.final_output,
        "total_duration_ms": result.total_duration_ms,
    }


@router.post("/execute/stream")
async def execute_task_stream(request: TaskRequest):
    async def event_generator():
        subscriber = await event_queue.subscribe()

        try:
            agents = create_agents(simulate_failure=request.simulate_failure)
            decomposer = Decomposer(planner_agent=agents["planner"], event_queue=event_queue)
            pipeline = Pipeline(agents=agents, event_queue=event_queue)

            async def run_pipeline():
                task = await decomposer.decompose(request.task)
                return await pipeline.execute(task)

            task = asyncio.create_task(run_pipeline())

            while not task.done():
                try:
                    event = await asyncio.wait_for(subscriber.get(), timeout=0.1)
                    yield f"data: {json.dumps({'type': event.type.value, 'data': event.data, 'timestamp': event.timestamp.isoformat()})}\n\n"
                except asyncio.TimeoutError:
                    continue

            result = task.result()
            yield f"data: {json.dumps({'type': 'complete', 'task_id': result.task_id, 'status': result.status.value, 'final_output': result.final_output})}\n\n"

        finally:
            event_queue.unsubscribe(subscriber)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/batch")
async def execute_batch(request: BatchTaskRequest):
    batch_processor = BatchProcessor(batch_size=request.batch_size, event_queue=event_queue)

    async def process_task(task_str: str):
        agents = create_agents()
        decomposer = Decomposer(planner_agent=agents["planner"], event_queue=event_queue)
        pipeline = Pipeline(agents=agents, event_queue=event_queue)
        task = await decomposer.decompose(task_str)
        result = await pipeline.execute(task)
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "final_output": result.final_output,
        }

    results = await batch_processor.process_batch(request.tasks, process_task)

    return {
        "total": len(results),
        "results": results,
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    subscriber = await event_queue.subscribe()

    try:
        while True:
            try:
                event = await asyncio.wait_for(subscriber.get(), timeout=1.0)
                await websocket.send_json({
                    "type": event.type.value,
                    "data": event.data,
                    "timestamp": event.timestamp.isoformat(),
                })
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
    finally:
        event_queue.unsubscribe(subscriber)
