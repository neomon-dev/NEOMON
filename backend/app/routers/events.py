import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.db import SessionFactory, get_session
from app.errors import BackendError
from app.models import Investigation, User

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def events(
    request: Request,
    investigation_id: uuid.UUID | None = Query(default=None),
    last_event_id_query: uuid.UUID | None = Query(default=None, alias="last_event_id"),
    last_event_id_header: str | None = Header(default=None, alias="Last-Event-ID"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    perm = PermissionService(session)
    if investigation_id is not None:
        await perm.check_investigation_access(user, investigation_id, "read")
    elif user.role != "admin":
        raise BackendError("investigation_id is required to subscribe to events.", 400, "investigation_id_required")

    broker = request.app.state.event_broker
    cursor_uuid: uuid.UUID | None = last_event_id_query
    if cursor_uuid is None and last_event_id_header:
        try:
            cursor_uuid = uuid.UUID(last_event_id_header.strip())
        except ValueError:
            cursor_uuid = None

    async def stream():
        # Subscribe before replaying so no events are missed between replay and live streaming.
        queue = broker.create_queue()
        seen_ids: set[uuid.UUID] = set()
        try:
            yield ": connected\n\n"
            if cursor_uuid is not None:
                replayed = await broker.replay_after(investigation_id, cursor_uuid)
                for event in replayed:
                    if await request.is_disconnected():
                        return
                    if investigation_id and event.payload.get("investigation_id") != str(investigation_id):
                        continue
                    if event.id in seen_ids:
                        continue
                    seen_ids.add(event.id)
                    yield (
                        f"id: {event.id}\n"
                        f"event: {event.event_type.value}\n"
                        f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
                    )

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if event.id in seen_ids:
                    continue
                if investigation_id and event.payload.get("investigation_id") != str(investigation_id):
                    continue
                seen_ids.add(event.id)
                yield (
                    f"id: {event.id}\n"
                    f"event: {event.event_type.value}\n"
                    f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
                )
        finally:
            broker.remove_queue(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
