from typing import Any, Callable, Awaitable, Optional
from streaming.events import EventQueue, EventType, Event
import asyncio
import logging

logger = logging.getLogger(__name__)


class BatchProcessor:
    def __init__(
        self,
        batch_size: int = 5,
        event_queue: Optional[EventQueue] = None,
    ):
        self.batch_size = batch_size
        self.event_queue = event_queue

    async def _emit_event(self, event_type: EventType, data: dict[str, Any]):
        if self.event_queue:
            event = Event(type=event_type, data=data)
            await self.event_queue.publish(event)

    async def process_batch(
        self,
        items: list[Any],
        processor: Callable[[Any], Awaitable[Any]],
    ) -> list[Any]:
        results = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size

        await self._emit_event(
            EventType.BATCH_START,
            {
                "total_items": len(items),
                "batch_size": self.batch_size,
                "total_batches": total_batches,
            },
        )

        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")

            batch_results = await asyncio.gather(
                *[processor(item) for item in batch],
                return_exceptions=True,
            )

            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch item {i + j} failed: {result}")
                    results.append({"error": str(result), "item_index": i + j})
                else:
                    results.append(result)

            await self._emit_event(
                EventType.BATCH_COMPLETE,
                {
                    "batch_num": batch_num,
                    "total_batches": total_batches,
                    "batch_size": len(batch),
                    "success_count": sum(1 for r in batch_results if not isinstance(r, Exception)),
                    "failure_count": sum(1 for r in batch_results if isinstance(r, Exception)),
                },
            )

        return results

    async def process_sequential(
        self,
        items: list[Any],
        processor: Callable[[Any], Awaitable[Any]],
    ) -> list[Any]:
        results = []
        await self._emit_event(
            EventType.BATCH_START,
            {
                "total_items": len(items),
                "batch_size": 1,
                "total_batches": len(items),
                "mode": "sequential",
            },
        )

        for i, item in enumerate(items):
            try:
                result = await processor(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Sequential item {i} failed: {e}")
                results.append({"error": str(e), "item_index": i})

            if (i + 1) % 10 == 0:
                await self._emit_event(
                    EventType.BATCH_COMPLETE,
                    {
                        "batch_num": i + 1,
                        "total_batches": len(items),
                        "progress": f"{i + 1}/{len(items)}",
                    },
                )

        return results
