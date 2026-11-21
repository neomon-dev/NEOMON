import pytest
from app.hardware.npu_service import NPUAuxiliaryService, RESEARCH_DOMAINS, COMPLEXITY_TIERS


def test_npu_auxiliary_service_initialization_and_classification():
    service = NPUAuxiliaryService()
    res = service.classify_query("Can green hydrogen become economically competitive with fossil fuels by 2035?")
    
    assert res.domain in RESEARCH_DOMAINS
    assert res.complexity in COMPLEXITY_TIERS
    assert res.latency_ms > 0.0
    assert isinstance(res.execution_device, str)
    assert len(res.execution_device) > 0


def test_npu_auxiliary_fallback_when_core_missing(monkeypatch):
    service = NPUAuxiliaryService()
    # Force _get_core to return None
    monkeypatch.setattr(service, "_get_core", lambda: None)
    
    res = service.classify_query("Does microplastic exposure cause cardiovascular toxicity?")
    assert res.is_fallback is True
    assert res.domain == "biomedical_sciences"
    assert res.complexity in COMPLEXITY_TIERS
