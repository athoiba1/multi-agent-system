import pytest
from orchestrator.batcher import BatchProcessor
from streaming.events import EventQueue


@pytest.fixture
def event_queue():
    return EventQueue()


@pytest.mark.asyncio
async def test_batch_size_respected(event_queue):
    processor = BatchProcessor(batch_size=2, event_queue=event_queue)
    items = list(range(10))
    batch_calls = []

    async def track_batch(item):
        batch_calls.append(item)
        return item

    results = await processor.process_batch(items, track_batch)
    assert len(results) == 10
    assert sorted(results) == list(range(10))


@pytest.mark.asyncio
async def test_sequential_mode(event_queue):
    processor = BatchProcessor(batch_size=5, event_queue=event_queue)
    items = [1, 2, 3]
    call_order = []

    async def track_order(item):
        call_order.append(item)
        return item * 10

    results = await processor.process_sequential(items, track_order)
    assert call_order == [1, 2, 3]
    assert results == [10, 20, 30]
