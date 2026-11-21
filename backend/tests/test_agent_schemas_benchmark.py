import json
import uuid
import pytest
from pydantic import ValidationError

from app.analysis.protocol import (
    ArgumentPayload,
    DebatePayload,
    DecisionPayload,
    PlannerPayload,
    ReportSectionPayload,
    ConfidenceAssessment,
)
from app.analysis.structured_parser import (
    extract_json_object,
    StructuredOutputError,
    JsonTruncationError,
    JsonRefusalError,
)

SAMPLE_CLAIM_ID = uuid.uuid4()
SAMPLE_EVIDENCE_ID = uuid.uuid4()
SAMPLE_SOURCE_ID = uuid.uuid4()
SAMPLE_ARGUMENT_ID = uuid.uuid4()


def test_planner_schema_variations():
    # 1. Clean JSON
    clean = json.dumps({
        "claims": [
            {
                "text": "Green hydrogen production cost will drop below $2 per kilogram.",
                "explanation": "Critical economic milestone for industrial parity.",
                "priority": 1,
                "search_objectives": ["electrolyzer capex", "lcoh 2035"],
                "evidence_categories": ["empirical", "economic"],
                "dependencies": [],
            }
        ]
    })
    res = extract_json_object(clean, response_model=PlannerPayload)
    assert len(res["claims"]) == 1

    # 2. Markdown fence + reasoning tags
    markdown_think = (
        f"<think>Analyzing energy market trends...</think>\n"
        f"```json\n{clean}\n```\nHope this helps!"
    )
    res2 = extract_json_object(markdown_think, response_model=PlannerPayload)
    assert len(res2["claims"]) == 1

    # 3. Trailing comma repair
    trailing_comma = clean.replace('"dependencies": []', '"dependencies": [],')
    res3 = extract_json_object(trailing_comma, response_model=PlannerPayload)
    assert len(res3["claims"]) == 1


def test_argument_schema_variations():
    clean_arg = json.dumps({
        "claim_id": str(SAMPLE_CLAIM_ID),
        "argument_type": "supporting",
        "text": "Empirical studies report 42% decrease in alkaline electrolyzer capital costs.",
        "evidence_ids": [str(SAMPLE_EVIDENCE_ID)],
        "source_ids": [str(SAMPLE_SOURCE_ID)],
        "evidence_basis": "direct",
        "reasoning_summary": "Based on peer-reviewed cost curves from IEA 2024.",
        "limitations": ["Limited to utility-scale installations"],
        "confidence": {
            "level": "strong",
            "explanation": "Triangulated across 3 independent market analyses.",
        },
    })

    # Wrap in arguments list
    payload = json.dumps({"arguments": [json.loads(clean_arg)]})
    
    # Preambles + reasoning
    messy = f"Here is the specialist analysis:\n<think>Evaluating evidence provenance</think>\n```json\n{payload}\n```"
    extracted = extract_json_object(messy)
    assert "arguments" in extracted
    validated = ArgumentPayload.model_validate(extracted["arguments"][0])
    assert validated.claim_id == SAMPLE_CLAIM_ID
    assert validated.confidence.level == "strong"


def test_debate_moderator_schema_variations():
    clean_debate = json.dumps({
        "round_number": 1,
        "moderator_summary": "Evaluated 12 arguments across 3 claims; persistent tension on grid power tariffs.",
        "unresolved_disagreements": ["Tariff volatility impact on LCOH"],
        "requested_follow_up": ["Verify off-peak PPA contract prices"],
    })
    messy = f"### Debate Round 1 Summary\n```json\n{clean_debate}\n```"
    res = extract_json_object(messy, response_model=DebatePayload)
    assert res["round_number"] == 1
    assert len(res["unresolved_disagreements"]) == 1


def test_conflict_adjudicator_schema_variations():
    clean_decision = json.dumps({
        "decisions": [
            {
                "claim_id": str(SAMPLE_CLAIM_ID),
                "decision": "moderately_supported",
                "explanation": "Supported by multiple independent studies with transparent methodology.",
                "supporting_argument_ids": [str(SAMPLE_ARGUMENT_ID)],
                "evidence_ids": [str(SAMPLE_EVIDENCE_ID)],
                "unresolved_disagreements": [],
            }
        ]
    })
    messy = f"<think>Weighing supporting vs contradicting evidence</think>\n{clean_decision}\nConcluded."
    extracted = extract_json_object(messy)
    decision = DecisionPayload.model_validate(extracted["decisions"][0])
    assert decision.decision == "moderately_supported"
    assert decision.claim_id == SAMPLE_CLAIM_ID


def test_schema_rejection_on_invalid_data():
    # Missing required 'explanation'
    invalid_claim = json.dumps({
        "claims": [
            {
                "text": "Short",  # <10 chars
                "priority": 10,   # >5
                "search_objectives": [],
                "evidence_categories": [],
            }
        ]
    })
    with pytest.raises(ValidationError):
        extract_json_object(invalid_claim, response_model=PlannerPayload)


def test_truncation_detection():
    truncated = '{"claims": [{"text": "Incomplete string that abruptly ends'
    with pytest.raises(JsonTruncationError):
        extract_json_object(truncated)


def test_refusal_detection():
    refusal = "I cannot fulfill this request as I am an AI language model."
    with pytest.raises(JsonRefusalError):
        extract_json_object(refusal)
