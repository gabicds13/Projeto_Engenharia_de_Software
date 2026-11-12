from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator


class DirectChatHub:
    def __init__(self) -> None:
        self._listeners: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def publish(
        self,
        channel_id: str,
        event: dict,
    ) -> None:
        listeners = list(self._listeners.get(channel_id, []))

        for queue in listeners:
            await queue.put(event)

    async def subscribe(
        self,
        channel_id: str,
    ) -> AsyncIterator[dict]:
        queue: asyncio.Queue = asyncio.Queue()

        self._listeners[channel_id].append(queue)

        try:
            while True:
                yield await queue.get()
        finally:
            listeners = self._listeners.get(channel_id, [])

            if queue in listeners:
                listeners.remove(queue)

            if not listeners:
                self._listeners.pop(channel_id, None)


direct_chat_hub = DirectChatHub()