# NEOMON — Hardware-Aware Multi-Device Scheduler Design

---

## 1. Overview & Problem Definition

In a multi-agent research architecture (Planner, Advocate, Skeptic, Methodology Auditor, Source Intelligence, Citation Genealogy), multiple agents become ready to execute simultaneously as upstream dependencies resolve. 

On a discrete server with 8x H100 GPUs, requests can be batched concurrently. However, on an Intel Core Ultra laptop with 16 GB shared memory and an integrated Arc GPU:
1. Running multiple concurrent `.generate()` calls on the same OpenVINO pipeline causes `can_allocate_blocks(1)` cache manager panics.
2. Initializing multiple separate pipeline instances on the iGPU would exhaust system RAM (each instance requires ~5.5 GB).
3. The scheduler must therefore serialize GPU access through an intelligent lease while maximizing parallel CPU execution for I/O and pre/post-processing.

---

## 2. Multi-Device Scheduler State Machine

```
              +---------------------------+
              | Agent Dependency Resolved |
              +---------------------------+
                            |
                            v
              +---------------------------+
              |  CPU Stage: Prompt Prep,  |
              | Retrieval & Serialization |
              +---------------------------+
                            |
                            v
              +---------------------------+
              | Hardware Queue Controller |
              +---------------------------+
                            |
            +---------------+---------------+
            |                               |
    [Profile: Balanced/Perf]         [Profile: Saver]
    Memory < 90%                     Memory >= 90%
            |                               |
            v                               v
    +---------------+               +---------------+
    | Arc GPU Lease |               | CPU Fallback  |
    | (1-slot FIFO) |               | (Bounded Ctx) |
    +---------------+               +---------------+
            |                               |
            +---------------+---------------+
                            |
                            v
              +---------------------------+
              | CPU Stage: JSON Repair,   |
              | Parsing & Pydantic Check  |
              +---------------------------+
                            |
                            v
              +---------------------------+
              | Result Storage & Telemetry|
              +---------------------------+
```

---

## 3. Scheduler Implementation Details

### A. Non-Reentrant GPU Mutex Lease
The OpenVINO server (`local_ai_analyzer/server.py`) maintains an asynchronous single-slot lock:
```python
async with gpu_inference_lock:
    # Dedicated access to Arc GPU pipeline
    output = pipeline.generate(prompt, max_new_tokens=max_tokens)
```
While one agent holds the GPU lease, other agents:
1. Synthesize their context and retrieve evidence on CPU.
2. Wait in a lightweight asynchronous queue with queue position tracking (`queue_position`, `queue_wait_seconds`).
3. Instantly acquire the lease the microsecond the active agent releases it.

### B. Dynamic Hardware Profiles
The scheduler exposes three dynamic profiles via `backend/app/hardware/telemetry.py`:

1. **`balanced` (Default):**
   - Device: Intel Arc Graphics (iGPU)
   - Concurrency: 1 GPU generation slot, infinite CPU async workers
   - Max Generation Tokens: 1,536 tokens
   - Memory Threshold: 88% RAM cap

2. **`performance`:**
   - Device: Intel Arc Graphics (iGPU) with prioritized scheduling
   - Concurrency: 1 GPU generation slot
   - Max Generation Tokens: 2,048 tokens
   - Memory Threshold: 92% RAM cap

3. **`memory_saver`:**
   - Device: Intel Arc Graphics with reduced KV-cache or CPU fallback
   - Concurrency: 1 GPU slot
   - Max Generation Tokens: 1,024 tokens
   - Memory Threshold: 75% RAM cap (forces aggressive GC after each agent execution)

---

## 4. Concurrency & Queue Observability

Each execution tracks granular hardware timing:
- `queue_wait_seconds`: Exact duration spent waiting for GPU lease.
- `ttft_ms`: Time to first token on the hardware.
- `tokens_per_second`: Effective generation throughput.
- `execution_device`: Hardware device string (e.g. `Intel Arc Graphics (iGPU)`).
- `duration_seconds`: Total end-to-end turnaround.

All metrics are returned in SSE streaming updates and rendered live in the NEOMON Observatory.
