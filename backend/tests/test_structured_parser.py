import uuid
import pytest
from pydantic import ValidationError

from app.analysis.protocol import PlannerPayload, ClaimPayload
from app.analysis.structured_parser import (
    StructuredOutputError,
    JsonTruncationError,
    JsonRefusalError,
    extract_balanced_json_substrings,
    extract_json_object,
    detect_truncation,
)


def test_extract_direct_json():
    raw = '{"claims": [{"text": "Sample claim text that is long enough", "explanation": "Valid", "priority": 1, "search_objectives": ["test"], "evidence_categories": ["empirical"], "dependencies": []}]}'
    result = extract_json_object(raw, response_model=PlannerPayload)
    assert len(result["claims"]) == 1
    assert result["claims"][0]["priority"] == 1


def test_extract_whitespace_padded_json():
    raw = '\n\n   {"claims": [{"text": "Sample claim text that is long enough", "explanation": "Valid", "priority": 2, "search_objectives": ["test"], "evidence_categories": ["empirical"], "dependencies": []}]}   \n\t'
    result = extract_json_object(raw, response_model=PlannerPayload)
    assert len(result["claims"]) == 1
    assert result["claims"][0]["priority"] == 2


def test_extract_markdown_fenced_json():
    raw = '''Here is the requested output:
```json
{
  "claims": [
    {
      "text": "Fenced claim text for testing purposes",
      "explanation": "Because testing is good",
      "priority": 3,
      "search_objectives": ["verify"],
      "evidence_categories": ["empirical"],
      "dependencies": []
    }
  ]
}
```
Hope this helps!'''
    result = extract_json_object(raw, response_model=PlannerPayload)
    assert len(result["claims"]) == 1
    assert result["claims"][0]["priority"] == 3


def test_extract_with_think_tags():
    raw = '''<think>
Let's analyze the question carefully. We need a valid JSON object matching PlannerPayload.
The claim needs priority 1.
</think>
```json
{
  "claims": [
    {
      "text": "Hydrogen storage requires high pressure composite tanks.",
      "explanation": "Storage thermodynamics are critical.",
      "priority": 1,
      "search_objectives": ["composite tank cost"],
      "evidence_categories": ["materials"],
      "dependencies": []
    }
  ]
}
```'''
    result = extract_json_object(raw, response_model=PlannerPayload)
    assert len(result["claims"]) == 1
    assert result["claims"][0]["text"].startswith("Hydrogen storage")


def test_extract_with_braces_inside_strings():
    raw = '''{
  "claims": [
    {
      "text": "The pattern {A} -> {B} shows {nested: value} relationships clearly.",
      "explanation": "Explanation with escaped \\"quotes\\" and {braces}.",
      "priority": 1,
      "search_objectives": ["objective {1}"],
      "evidence_categories": ["category {A}"],
      "dependencies": []
    }
  ]
}'''
    result = extract_json_object(raw, response_model=PlannerPayload)
    assert len(result["claims"]) == 1
    assert "{nested: value}" in result["claims"][0]["text"]


def test_detect_truncation():
    # Truncated in the middle of a string
    raw = '{"claims": [{"text": "Incomplete claim text'
    assert detect_truncation(raw) is True

    # Truncated with open brace
    raw2 = '{"claims": [{'
    assert detect_truncation(raw2) is True

    with pytest.raises(JsonTruncationError):
        extract_json_object(raw)


def test_refusal_detection():
    raw = "I cannot fulfill this request as an AI assistant."
    with pytest.raises(JsonRefusalError):
        extract_json_object(raw)


def test_empty_content():
    with pytest.raises(StructuredOutputError):
        extract_json_object("")
    with pytest.raises(StructuredOutputError):
        extract_json_object("   \n\t  ")


def test_schema_validation_failure():
    # Missing required 'search_objectives'
    raw = '{"claims": [{"text": "Missing objectives claim text", "explanation": "Valid", "priority": 1}]}'
    with pytest.raises(ValidationError):
        extract_json_object(raw, response_model=PlannerPayload)


def test_extra_forbidden_fields():
    # extra="forbid" in ClaimPayload
    raw = '{"claims": [{"text": "Sample claim text that is long enough", "explanation": "Valid", "priority": 1, "search_objectives": ["test"], "evidence_categories": ["empirical"], "dependencies": [], "hallucinated_field": 123}]}'
    with pytest.raises(ValidationError):
        extract_json_object(raw, response_model=PlannerPayload)
