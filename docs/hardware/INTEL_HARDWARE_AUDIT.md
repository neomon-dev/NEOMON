# NEOMON — Intel Hardware Audit & Baseline Profiling Report

**Target Platform:** Intel Core Ultra 5 125H (Meteor Lake)  
**Host Architecture:** x86_64 / Windows 11  
**System Memory:** 16 GB LPDDR5 Dual-Channel (Shared System & USM Memory)  
**Storage:** 512 GB NVMe SSD  
**Inference Engine:** OpenVINO GenAI 2024.x / Uvicorn OpenAI-compatible Server  

---

## 1. Executive Summary & Hardware Topology

NEOMON was audited on the target laptop hardware to diagnose inference latency, memory pressure, and misattributions observed during multi-agent research runs. 

OpenVINO `Core().available_devices` query confirmed the presence of three distinct compute engines on the Intel Core Ultra 5 125H platform:

```json
{
  "cpu": {
    "device": "CPU",
    "name": "Intel(R) Core(TM) Ultra 5 125H",
    "topology": "14 cores / 18 threads (4 Performance Cores, 8 Efficient Cores, 2 Low-Power Island E-Cores)",
    "capabilities": ["FP32", "FP16", "INT8", "AVX2", "AVX-VNNI", "Dynamic Dequantization", "Dynamic Tensors"]
  },
  "gpu": {
    "device": "GPU",
    "name": "Intel(R) Arc(TM) Graphics (iGPU)",
    "architecture": "Xe-LPG (vendor=0x8086 arch=v12.71.4)",
    "memory_model": "Unified Shared Memory (USM) dynamically carved from 16 GB LPDDR5 system RAM",
    "capabilities": ["FP32", "FP16", "INT8", "INT4 / WNA4 / Dynamic Dequantization"]
  },
  "npu": {
    "device": "NPU",
    "name": "Intel(R) AI Boost",
    "version": "NPU 3720 (VPUX)",
    "capabilities": ["FP16", "INT8 Static Quantization", "Static Shape Compilations"]
  }
}
```

---

## 2. Root Cause Analysis: The `rule_based` UI Discrepancy

During earlier testing, user inspection of the Agent Execution Pool revealed agent cards displaying `rule_based` execution while OpenVINO was actively running and GPU utilization reached 92%.

### Root Cause
Investigation of `backend/app/analysis/service.py` and `app/investigations/[id]/page.tsx` revealed:
1. In `app/investigations/[id]/page.tsx:1521`, the frontend rendered:
   ```tsx
   {execution.model ?? "rule_based"}
   ```
2. When jobs were dispatched, `_create_execution(job.id, role, role_models.get(role))` was invoked. Because `role_models` did not have an explicit mapping for every dynamic agent role, `execution.model` was saved to SQLite as `None`.
3. Consequently, the frontend fell back to displaying `"rule_based"`, giving the false impression that a fallback mock was running, even though the agent had waited 186.9s on the OpenVINO LLM endpoint.
4. Furthermore, when OpenVINO Qwen3-8B generated conversational chain-of-thought (`<think>`), the planner failed strict `json.loads` parsing, producing the error `planner failed: model response did not contain a valid JSON object`.

### Implemented Fix
1. In `backend/app/analysis/service.py`, `effective_model = model or job.default_model or "openvino-qwen3-8b"` ensures the actual model is always persisted.
2. In `backend/app/providers/openai_compatible.py`, device headers (`execution_device: Intel Arc Graphics (iGPU)`) and performance metrics (`ttft_ms`, `tokens_per_second`) are returned and stored in execution records.
3. In `backend/app/utils/structured_parser.py`, robust multi-strategy JSON extraction eliminates JSON decode failures from thinking tags and markdown fences.

---

## 3. Empirical Device Capability & Constraint Matrix

| Evaluation Dimension | Intel Core Ultra 5 125H CPU | Intel Arc Graphics (Xe-LPG iGPU) | Intel AI Boost NPU (NPU 3720) |
| :--- | :--- | :--- | :--- |
| **Model Evaluated** | `Qwen2.5-7B-Instruct-int4-ov` | `Qwen2.5-7B-Instruct-int4-ov` | `Qwen2.5-7B-Instruct-int4-ov` / Embeddings |
| **Compilation Status** | Succeeded (Dynamic Shapes) | Succeeded (Optimized Kernel Cache) | **Compilation Failed** (`DynamicDequantizeOp`) |
| **Error / Diagnostic** | None | None | `Unsupported DynamicDequantizeOp: inElemType=!quant.uniform<u4:f16>` |
| **Time to First Token (TTFT)** | **12,609.6 ms** (12.6s) | **654.3 ms** (**19.3x faster**) | Incompatible with INT4 LLMs |
| **Generation Speed (TPS)** | **7.17 tokens/sec** | **12.53 tokens/sec** (**1.75x faster**) | Incompatible with INT4 LLMs |
| **Total Turnaround (248 tok)**| **47.05 seconds** | **20.37 seconds** (**2.3x faster**) | N/A |
| **Memory Footprint** | System RAM | USM (System RAM allocation) | Static SRAM / Dedicated VPU Buffers |
| **Recommended Workload** | Async DAG, JSON Parsing, Validation | Primary Multi-Agent LLM Generation | Observability & Future Static INT8 Models |

---

## 4. Hardware Bottleneck Identification

1. **Integrated GPU Unified Shared Memory (USM) Pressure:**  
   Because the Intel Arc iGPU does not have dedicated discrete VRAM (GDDR6), it allocates its KV-cache and weights directly from system LPDDR5 RAM. Under peak load, memory consumption reached 14.38 GB / 15.57 GB (92.3%).
2. **GenAI Pipeline Concurrency Limitation:**  
   Attempting concurrent `.generate()` calls on a single `LLMPipeline` instance triggered an OpenVINO crash:
   `Check 'can_allocate_blocks(1)' failed at continuous_batching/cache/block_manager.hpp:525`.  
   Therefore, multi-agent inference must be serialized on the Arc GPU using a single-slot FIFO queue lease, while CPU threads execute asynchronous data harvesting, DAG orchestration, and JSON validation in parallel.
