import pytest
from app.hardware.telemetry import hardware_service, MemoryProfile


def test_hardware_telemetry_detection():
    data = hardware_service.get_telemetry()
    assert data.cpu.name == "Intel Core Ultra 5 125H"
    assert data.cpu.device_type == "CPU"
    assert data.cpu.properties["cores"] == 14
    assert data.cpu.properties["threads"] == 18

    assert data.gpu.name == "Intel Arc Graphics (iGPU)"
    assert data.gpu.device_type == "GPU"
    assert data.gpu.properties["optimal_ttft_ms"] == 654.3
    assert data.gpu.properties["throughput_tps"] == 12.53

    assert data.npu.name == "Intel AI Boost NPU"
    assert data.npu.device_type == "NPU"
    assert "INT4 dynamic dequant" in data.npu.properties["limitation"]

    assert data.memory.total_gb > 0
    assert data.memory.available_gb > 0
    assert data.memory.used_percent > 0


def test_memory_profile_transitions():
    balanced = hardware_service.set_profile(MemoryProfile.BALANCED)
    assert balanced["max_tokens"] == 1536
    assert balanced["backpressure_threshold_percent"] == 85.0
    assert hardware_service.profile == MemoryProfile.BALANCED

    perf = hardware_service.set_profile(MemoryProfile.PERFORMANCE)
    assert perf["max_tokens"] == 2048
    assert perf["backpressure_threshold_percent"] == 92.0
    assert hardware_service.profile == MemoryProfile.PERFORMANCE

    saver = hardware_service.set_profile(MemoryProfile.MEMORY_SAVER)
    assert saver["max_tokens"] == 768
    assert saver["backpressure_threshold_percent"] == 75.0
    assert hardware_service.profile == MemoryProfile.MEMORY_SAVER

    # Reset back to balanced
    hardware_service.set_profile(MemoryProfile.BALANCED)
