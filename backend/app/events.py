import asyncio
import json
import uuid
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Investigation, ResearchEvent
from app.schemas import EventType, ResearchEventMessage


class EventBroker:
    def __init__(
        self,
        max_queue_size: int = 100,
        max_history_size: int = 500,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._subscribers: set[asyncio.Queue[ResearchEventMessage]] = set()
        self._max_queue_size = max_queue_size
        self._history: deque[ResearchEventMessage] = deque(maxlen=max_history_size)
        self._session_factory = session_factory
        self._persist_lock = asyncio.Lock()

    def configure_persistence(self, session_factory: async_sessionmaker[AsyncSession] | None) -> None:
        self._session_factory = session_factory

    async def publish(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        *,
        session: AsyncSession | None = None,
    ) -> ResearchEventMessage:
        event = ResearchEventMessage(
            id=uuid.uuid4(),
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        self._history.append(event)
        if session is not None or self._session_factory is not None:
            await self._persist_event(event, session=session)
        for queue in tuple(self._subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)
        return event

    async def _persist_event(
        self,
        event: ResearchEventMessage,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        raw_investigation_id = event.payload.get("investigation_id")
        investigation_uuid: uuid.UUID | None = None
        if isinstance(raw_investigation_id, str):
            try:
                investigation_uuid = uuid.UUID(raw_investigation_id)
            except ValueError:
                investigation_uuid = None

        async def _write(target_session: AsyncSession) -> None:
            nonlocal investigation_uuid
            if investigation_uuid is not None:
                exists = await target_session.get(Investigation, investigation_uuid)
                if exists is None:
                    investigation_uuid = None
            target_session.add(
                ResearchEvent(
                    id=event.id,
                    investigation_id=investigation_uuid,
                    event_type=event.event_type.value,
                    payload=json.dumps(event.payload, default=str),
                    created_at=event.created_at,
                )
            )

        if session is not None:
            await _write(session)
            return
        if self._session_factory is None:
            return
        async with self._persist_lock:
            async with self._session_factory() as new_session:
                await _write(new_session)
                await new_session.commit()

    async def replay_after(
        self,
        investigation_id: uuid.UUID | None,
        last_event_id: uuid.UUID,
    ) -> list[ResearchEventMessage]:
        """Return persisted/buffered events strictly after last_event_id within scope."""
        if self._session_factory is not None:
            async with self._session_factory() as session:
                stmt = select(ResearchEvent).order_by(ResearchEvent.created_at.asc(), ResearchEvent.id.asc())
                if investigation_id is not None:
                    stmt = stmt.where(ResearchEvent.investigation_id == investigation_id)
                rows = list((await session.scalars(stmt)).all())
                cursor_index = next((idx for idx, row in enumerate(rows) if row.id == last_event_id), None)
                if cursor_index is None:
                    return []
                replayed: list[ResearchEventMessage] = []
                for row in rows[cursor_index + 1 :]:
                    try:
                        event_type = EventType(row.event_type)
                    except ValueError:
                        continue
                    replayed.append(
                        ResearchEventMessage(
                            id=row.id,
                            event_type=event_type,
                            payload=json.loads(row.payload),
                            created_at=row.created_at or datetime.now(UTC),
                        )
                    )
                return replayed

        scoped = [
            item
            for item in self._history
            if investigation_id is None or item.payload.get("investigation_id") == str(investigation_id)
        ]
        cursor_index = next((idx for idx, item in enumerate(scoped) if item.id == last_event_id), None)
        if cursor_index is None:
            return []
        return scoped[cursor_index + 1 :]

    async def subscribe(self) -> AsyncIterator[ResearchEventMessage]:
        queue: asyncio.Queue[ResearchEventMessage] = asyncio.Queue(self._max_queue_size)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)

    def create_queue(self) -> asyncio.Queue[ResearchEventMessage]:
        queue: asyncio.Queue[ResearchEventMessage] = asyncio.Queue(self._max_queue_size)
        self._subscribers.add(queue)
        return queue

    def remove_queue(self, queue: asyncio.Queue[ResearchEventMessage]) -> None:
        self._subscribers.discard(queue)
