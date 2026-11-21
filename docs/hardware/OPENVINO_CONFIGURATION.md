# NEOMON — OpenVINO GenAI Configuration & Tuning Guide

---

## 1. Environment & Setup

- **Python Runtime:** `C:\Users\mohid\openvino_env\Scripts\python.exe`
- **OpenVINO Version:** 2024.5 / OpenVINO GenAI 2024.x
- **Inference Server Script:** `C:\Users\mohid\local_ai_analyzer\server.py`
- **Default Port:** `8000`
- **Default Endpoint:** `http://127.0.0.1:8000/v1`

---

## 2. Recommended OpenVINO Model Configuration

### Model Details
- **Architecture:** Qwen 2.5 7B Instruct
- **Weight Precision:** INT4 (Symmetric/Asymmetric Dynamic Quantization)
- **Local Directory:** `C:\Users\mohid\.cache\lm-studio\models\qwen2.5-7b-instruct-int4-ov`
- **Target Device:** `GPU` (Intel Arc Xe-LPG)

### Optimal Pipeline Parameters
```python
import openvino_genai as ov_genai

# Pipeline Initialization on Intel Arc GPU
pipeline = ov_genai.LLMPipeline(
    model_path=model_dir,
    device="GPU"
)

# Generation Configuration
config = ov_genai.GenerationConfig()
config.max_new_tokens = 1536
config.temperature = 0.2
config.top_p = 0.9
```

---

## 3. Intel Arc GPU Specific Optimizations

1. **Kernel Cache Directory:**  
   Set the OpenVINO cache folder to reduce model load latency from 15 seconds to under 2 seconds on subsequent launches:
   ```powershell
   $env:OV_CACHE_DIR = "C:\Users\mohid\.cache\openvino_cl_cache"
   ```
2. **Unified Shared Memory (USM) Host Pointer Pinning:**  
   OpenVINO directly maps prompt tokens from host memory into Xe-LPG execution units with zero copy, reducing CPU-GPU transfer overhead to near-zero.
3. **Warmup Turn:**  
   During server initialization, a dummy 1-token generation warmup is executed:
   ```python
   pipeline.generate("warmup", max_new_tokens=1)
   ```
   This ensures OpenCL kernels and compilation shaders are fully resident in memory before the first agent prompt arrives, eliminating first-request latency spikes.

---

## 4. Telemetry Endpoint Specification

The OpenVINO server exposes `/v1/hardware` and `/hardware` diagnostic endpoints:

```json
{
  "status": "healthy",
  "active_device": "GPU",
  "device_name": "Intel(R) Arc(TM) Graphics (iGPU)",
  "available_devices": ["CPU", "GPU", "NPU"],
  "model": "openvino-qwen3-8b",
  "concurrency_limit": 1
}
```

Every response to `/v1/chat/completions` includes exact timing in the `usage` object:
```json
{
  "usage": {
    "prompt_tokens": 142,
    "completion_tokens": 248,
    "total_tokens": 390,
    "ttft_ms": 654.3,
    "tokens_per_second": 12.53,
    "duration_seconds": 20.37,
    "execution_device": "Intel Arc Graphics (iGPU)"
  }
}
```
