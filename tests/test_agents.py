import pytest
import asyncio
from models.task import Task, Step, StepStatus
from models.results import StepResult, PipelineResult, ResultStatus
from streaming.events import EventQueue, Event, EventType
from orchestrator.batcher import BatchProcessor


@pytest.fixture
def event_queue():
    return EventQueue()


@pytest.fixture
def batch_processor(event_queue):
    return BatchProcessor(batch_size=3, event_queue=event_queue)


def test_step_creation():
    step = Step(
        name="test_step",
        description="A test step",
        agent_type="retriever",
    )
    assert step.name == "test_step"
    assert step.status == StepStatus.PENDING
    assert step.agent_type == "retriever"


def test_task_creation():
    task = Task(original_request="Test request")
    assert task.original_request == "Test request"
    assert task.status == "pending"
    assert len(task.steps) == 0


def test_step_result():
    result = StepResult(
        step_id="123",
        step_name="test",
        status=ResultStatus.SUCCESS,
        output_data={"key": "value"},
    )
    assert result.status == ResultStatus.SUCCESS
    assert result.output_data == {"key": "value"}


def test_pipeline_result():
    result = PipelineResult(
        task_id="task-123",
        status=ResultStatus.SUCCESS,
        final_output={"report": "test"},
    )
    assert result.task_id == "task-123"
    assert result.status == ResultStatus.SUCCESS


@pytest.mark.asyncio
async def test_event_queue_publish(event_queue):
    event = Event(type=EventType.SYSTEM, data={"message": "test"})
    await event_queue.publish(event)
    assert not event_queue._queue.empty()


@pytest.mark.asyncio
async def test_event_queue_subscribe(event_queue):
    subscriber = await event_queue.subscribe()
    event = Event(type=EventType.SYSTEM, data={"message": "test"})
    await event_queue.publish(event)
    received = await subscriber.get()
    assert received.type == EventType.SYSTEM
    event_queue.unsubscribe(subscriber)


@pytest.mark.asyncio
async def test_batch_processor_sequential(batch_processor):
    items = [1, 2, 3, 4, 5]

    async def processor(item):
        return item * 2

    results = await batch_processor.process_sequential(items, processor)
    assert results == [2, 4, 6, 8, 10]


@pytest.mark.asyncio
async def test_batch_processor_batch(batch_processor):
    items = [1, 2, 3, 4, 5]

    async def processor(item):
        return item * 2

    results = await batch_processor.process_batch(items, processor)
    assert sorted(results) == [2, 4, 6, 8, 10]


@pytest.mark.asyncio
async def test_batch_processor_error_handling(batch_processor):
    items = [1, 2, 3]

    async def processor(item):
        if item == 2:
            raise ValueError("Test error")
        return item * 2

    results = await batch_processor.process_batch(items, processor)
    assert len(results) == 3
    assert any(isinstance(r, dict) and "error" in r for r in results)
