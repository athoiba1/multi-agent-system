import pytest
import asyncio
from orchestrator.pipeline import Pipeline
from orchestrator.decomposer import Decomposer
from models.task import Task, Step
from streaming.events import EventQueue


@pytest.fixture
def event_queue():
    return EventQueue()


@pytest.mark.asyncio
async def test_topological_sort():
    pipeline = Pipeline(agents={})

    task = Task(
        original_request="test",
        steps=[
            Step(name="write", description="Write", agent_type="writer", dependencies=["analyze"]),
            Step(name="analyze", description="Analyze", agent_type="analyzer", dependencies=["retrieve"]),
            Step(name="retrieve", description="Retrieve", agent_type="retriever", dependencies=[]),
        ],
    )

    ordered = pipeline._topological_sort(task)
    step_names = [s.name for s in ordered]

    assert step_names.index("retrieve") < step_names.index("analyze")
    assert step_names.index("analyze") < step_names.index("write")


@pytest.mark.asyncio
async def test_get_ready_steps():
    pipeline = Pipeline(agents={})

    task = Task(
        original_request="test",
        steps=[
            Step(name="step1", description="Step 1", agent_type="retriever", dependencies=[]),
            Step(name="step2", description="Step 2", agent_type="analyzer", dependencies=["step1"]),
        ],
    )

    ready = pipeline._get_ready_steps(task)
    assert len(ready) == 1
    assert ready[0].name == "step1"

    task.steps[0].status = "completed"
    ready = pipeline._get_ready_steps(task)
    assert len(ready) == 1
    assert ready[0].name == "step2"
