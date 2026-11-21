# NEOMON — Heterogeneous Compute Architecture
## Intel Core Ultra 5 (CPU + Arc GPU + NPU) Tri-Engine Orchestration

---

## 1. Architectural Philosophy

Running a high-throughput, multi-agent AI research network on a resource-constrained 16 GB laptop requires treating the platform not as an undifferentiated CPU, but as an asymmetric heterogeneous compute cluster consisting of three distinct silicon engines:

1. **Intel Arc Graphics (Xe-LPG iGPU):** Throughput-dense matrix engine dedicated exclusively to INT4/FP16 Large Language Model inference.
2. **Intel Core Ultra 5 125H (CPU):** 14-core hybrid orchestrator managing asynchronous I/O, prompt synthesis, vector operations, structured JSON extraction, and Pydantic validation.
3. **Intel AI Boost (NPU 3720):** Ultra-low-power neural accelerator dedicated to continuous telemetry sampling, background anomaly detection, and future static INT8 embeddings.

```
                      +------------------------------------------+
                      |         NEOMON Async Multi-Agent         |
                      |          Orchestration Engine            |
                      +------------------------------------------+
                                           |
                   +-----------------------+-----------------------+
                   |                       |                       |
                   v                       v                       v
      +------------------------+  +-----------------+  +----------------------+
      |   Intel Core Ultra     |  |    Intel Arc    |  |    Intel AI Boost    |
      |       125H CPU         |  |   Xe-LPG iGPU   |  |       NPU 3720       |
      +------------------------+  +-----------------+  +----------------------+
      | - Async DAG Dispatch   |  | - INT4 Qwen3-8B |  | - Telemetry Polling  |
      | - Source Ingestion     |  | - TTFT: 654 ms  |  | - Hardware Auditing  |
      | - Regex/JSON Parsing   |  | - TPS: 12.5 tps |  | - VPU Driver Metrics |
      | - Pydantic Validation  |  | - Mutex Lease   |  |                      |
      | - Dynamic Embeddings   |  | - USM Allocation|  |                      |
      +------------------------+  +-----------------+  +----------------------+
```

---

## 2. Workload Partitioning by Silicon Engine

### A. Intel Arc GPU Workload (Inference Master)
- **Assigned Models:** `openvino-qwen3-8b` (`Qwen2.5-7B-Instruct-int4-ov`).
- **Memory Allocation:** Unified Shared Memory (USM) dynamic buffer (approximately 5.8 GB working set for INT4 weights and 4K KV-cache).
- **Execution Policy:** Single-slot FIFO queue with non-reentrant mutex. Prevents KV-cache memory thrashing and guarantees predictable execution.
- **Measured Latency:** 654.3 ms TTFT (compared to 12,609.6 ms on CPU).

### B. Intel Core Ultra 5 125H CPU Workload (System Orchestrator)
- **Thread Allocation:**
  - 4 Performance Cores (P-Cores): Vector similarity search, dynamic text embeddings (1236 ms latency), and compute-intensive JSON repair algorithms.
  - 8 Efficient Cores (E-Cores): FastAPI server, SQLite transactions, HTTP client SSE streaming, and async agent task scheduling.
  - 2 Low-Power Island E-Cores (LPE): Background heartbeat polling and system metrics monitoring.
- **Failover / Fallback:** Bounded CPU fallback with 2048 token context truncation if USM exceeds safety thresholds.

### C. Intel AI Boost NPU Workload (Continuous Background Monitor)
- **Role:** Dedicated hardware diagnostics and persistent device telemetry.
- **VPUX Compiler Constraints:** Current NPU 3720 hardware microarchitecture does not support dynamic dequantization operations (`Unsupported DynamicDequantizeOp: inElemType=!quant.uniform<u4:f16>`). Therefore, generative autoregressive LLMs remain offloaded to the Arc GPU, preventing runtime compilation panics.

---

## 3. Memory & Unified Shared Memory (USM) Safeguards

Because system RAM and GPU memory share the same 16 GB physical LPDDR5 bus, memory contention can trigger Windows paging file thrashing. NEOMON establishes strict memory boundaries:

1. **System Thresholds:**
   - Safe Operating Zone: < 80% RAM utilization (full GPU acceleration enabled).
   - High Memory Pressure Zone: 80% - 90% RAM utilization (KV-cache budget reduced to 2048 tokens).
   - Critical Safety Floor: > 92% RAM utilization (backpressure applied, queue delays introduced, garbage collection forced).
2. **Dynamic Profiling:**
   The user or system can select between `balanced`, `performance`, and `memory_saver` execution profiles at runtime via the Agent Observatory UI or REST API (`POST /api/v1/hardware/profile`).
