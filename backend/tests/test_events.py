import asyncio
import json
import uuid

import pytest

from app.events import EventBroker
from app.schemas import EventType


@pytest.mark.asyncio
async def test_event_broker_delivers_typed_events():
    broker = EventBroker()
    stream = broker.subscribe()
    next_event = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0)
    await broker.publish(EventType.agent_started, {"agent": "skeptic"})
    event = await asyncio.wait_for(next_event, timeout=1)
    await stream.aclose()

    assert event.event_type is EventType.agent_started
    assert event.payload == {"agent": "skeptic"}
    assert len(broker._subscribers) == 0


@pytest.mark.asyncio
async def test_event_broker_replays_in_order_and_enforces_investigation_isolation():
    broker = EventBroker()
    inv_a = str(uuid.uuid4())
    inv_b = str(uuid.uuid4())

    e1 = await broker.publish(EventType.analysis_queued, {"investigation_id": inv_a, "seq": 1})
    e_other = await broker.publish(EventType.analysis_queued, {"investigation_id": inv_b, "seq": 99})
    e2 = await broker.publish(EventType.analysis_stage_changed, {"investigation_id": inv_a, "seq": 2})
    e3 = await broker.publish(EventType.analysis_completed, {"investigation_id": inv_a, "seq": 3})

    replayed = await broker.replay_after(uuid.UUID(inv_a), e1.id)
    assert [item.id for item in replayed] == [e2.id, e3.id]
    assert all(item.payload["investigation_id"] == inv_a for item in replayed)

    # Cross-investigation cursor must never leak events from another investigation
    assert await broker.replay_after(uuid.UUID(inv_a), e_other.id) == []
    # Unknown / expired cursor returns empty safely
    assert await broker.replay_after(uuid.UUID(inv_a), uuid.uuid4()) == []


def test_sse_endpoint_replays_with_last_event_id_and_validates_investigation(client):
    from app.db import SessionFactory
    from app.models import Investigation

    async def seed():
        async with SessionFactory() as session:
            inv = Investigation(question="Does SSE replay preserve order?", mode="quick")
            session.add(inv)
            await session.commit()
            return inv.id

    inv_id = client.portal.call(seed)
    try:
        # Unknown investigation returns 404
        missing = client.get(f"/api/v1/events?investigation_id={uuid.uuid4()}")
        assert missing.status_code == 404

        broker = client.app.state.event_broker

        async def publish_events():
            first = await broker.publish(
                EventType.analysis_stage_changed, {"investigation_id": str(inv_id), "stage": "planning"}
            )
            second = await broker.publish(
                EventType.analysis_completed, {"investigation_id": str(inv_id), "status": "completed"}
            )
            return first, second

        first_event, second_event = client.portal.call(publish_events)
        replayed = client.portal.call(broker.replay_after, inv_id, first_event.id)
        assert [item.id for item in replayed] == [second_event.id]
        assert json.loads(json.dumps(replayed[0].model_dump(mode="json")))["id"] == str(second_event.id)
    finally:
        async def cleanup():
            from sqlalchemy import delete
            from app.models import ResearchEvent
            async with SessionFactory() as session:
                await session.execute(delete(ResearchEvent).where(ResearchEvent.investigation_id == inv_id))
                await session.execute(delete(Investigation).where(Investigation.id == inv_id))
                await session.commit()

        client.portal.call(cleanup)


@pytest.mark.asyncio
async def test_event_broker_publish_reuses_caller_session_without_sqlite_lock(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.models import Base, Investigation, ResearchEvent

    db_path = tmp_path / "lock_check.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 1})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    broker = EventBroker(session_factory=factory)

    async with factory() as session:
        inv = Investigation(question="Avoid SQLite write self-deadlock", mode="quick", status="running")
        session.add(inv)
        await session.flush()

        # Previously, publishing here opened a second SQLite writer connection and deadlocked.
        published = await broker.publish(
            EventType.research_started,
            {"investigation_id": str(inv.id), "question": inv.question},
            session=session,
        )
        await session.commit()

    async with factory() as verify_session:
        row = await verify_session.get(ResearchEvent, published.id)
        assert row is not None
        assert row.investigation_id == inv.id
        assert row.event_type == EventType.research_started.value

    await engine.dispose()
