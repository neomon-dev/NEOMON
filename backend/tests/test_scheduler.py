import asyncio
import pytest
from app.analysis.scheduler import AdaptiveGPUScheduler


@pytest.mark.asyncio
async def test_gpu_scheduler_single_slot_serialization():
    scheduler = AdaptiveGPUScheduler(initial_profile="balanced")
    assert scheduler.max_slots == 1

    execution_order: list[str] = []

    async def worker(name: str, delay: float):
        async with scheduler.lease(name, estimated_prompt_tokens=300):
            execution_order.append(f"{name}_start")
            await asyncio.sleep(delay)
            execution_order.append(f"{name}_end")

    # Launch two workers concurrently
    t1 = asyncio.create_task(worker("worker1", 0.05))
    await asyncio.sleep(0.01)  # Ensure worker1 acquires lease first
    t2 = asyncio.create_task(worker("worker2", 0.02))

    await asyncio.gather(t1, t2)

    # Worker 1 must complete before Worker 2 starts
    assert execution_order == ["worker1_start", "worker1_end", "worker2_start", "worker2_end"]

    telemetry = scheduler.get_telemetry()
    assert telemetry.total_leased_requests == 2
    assert telemetry.active_generations == 0
    assert telemetry.queue_depth == 0
    assert telemetry.total_queue_wait_seconds > 0.0


@pytest.mark.asyncio
async def test_gpu_scheduler_telemetry_reporting():
    scheduler = AdaptiveGPUScheduler(initial_profile="performance")
    telemetry = scheduler.get_telemetry()
    assert telemetry.current_profile == "performance"
    assert telemetry.max_concurrent_slots == 1
    assert telemetry.backpressure_active is False
