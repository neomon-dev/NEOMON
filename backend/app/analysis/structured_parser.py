import json
import logging
import re
from typing import Any
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN_RE = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([\]\}])")
_REFUSAL_RE = re.compile(
    r"^\s*(I cannot|I am unable to|As an AI|I'm sorry|I can't|I am sorry)\b",
    re.IGNORECASE,
)


class StructuredOutputError(ValueError):
    """Base exception for structured output extraction failures."""
    pass


class JsonTruncationError(StructuredOutputError):
    """Raised when the model response appears truncated mid-JSON."""
    pass


class JsonRefusalError(StructuredOutputError):
    """Raised when the model output constitutes a refusal."""
    pass


def extract_balanced_json_substrings(text: str) -> list[str]:
    """Extract top-level balanced `{ ... }` candidate substrings without using fragile regex.
    
    Correctly skips string literals (including escaped quotes and braces inside strings).
    """
    candidates: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "{":
            start = i
            depth = 0
            in_string = False
            escape = False
            j = i
            closed = False
            while j < n:
                ch = text[j]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            candidates.append(text[start : j + 1])
                            i = j
                            closed = True
                            break
                j += 1
            if not closed and depth > 0:
                # We reached the end of the text with unclosed braces -> truncation detected
                break
        i += 1
    return candidates


def detect_truncation(text: str) -> bool:
    """Return True if the text ends with an open brace or unclosed string."""
    i = 0
    n = len(text)
    depth = 0
    in_string = False
    escape = False
    has_seen_brace = False
    while i < n:
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
                has_seen_brace = True
            elif ch == "}":
                if depth > 0:
                    depth -= 1
        i += 1
    return (has_seen_brace and depth > 0) or in_string


def extract_json_object(
    raw_content: str,
    *,
    response_model: type[BaseModel] | None = None,
) -> dict[str, Any]:
    """Decode a single valid JSON object from raw model content.

    Features:
    1. Direct JSON objects and whitespace-padded JSON.
    2. Markdown fenced JSON (```json ... ```).
    3. Stripping of reasoning/thinking tags (<think>...</think>).
    4. Balanced character-scanning extraction that handles braces/escapes inside strings.
    5. Rejection of empty content, explicit refusals, and truncated outputs.
    6. Candidate validation against response_model when provided.
    7. No silent fabrication of missing fields or invalid evidence.
    """
    if not isinstance(raw_content, str) or not raw_content.strip():
        raise StructuredOutputError("model response is empty")

    trimmed = raw_content.strip()

    # Refusal check
    if _REFUSAL_RE.match(trimmed) and not ("{" in trimmed and "}" in trimmed):
        raise JsonRefusalError("model returned a refusal")

    # Strip completed thinking tags
    cleaned = _THINK_TAG_RE.sub("", trimmed).strip()
    if not cleaned:
        # If text had an unclosed <think> tag that consumed everything
        if _THINK_OPEN_RE.search(trimmed):
            raise JsonTruncationError("model output truncated inside thinking tags")
        cleaned = trimmed

    last_validation_error: ValidationError | None = None

    # 1. Attempt direct parse of cleaned text
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            if response_model is not None:
                response_model.model_validate(parsed)
            return parsed
    except ValidationError as val_err:
        last_validation_error = val_err
    except json.JSONDecodeError:
        pass

    # 2. Attempt markdown code fence extraction
    for match in _JSON_FENCE_RE.finditer(cleaned):
        cand_str = match.group(1).strip()
        try:
            parsed = json.loads(cand_str)
            if isinstance(parsed, dict):
                if response_model is not None:
                    response_model.model_validate(parsed)
                return parsed
        except ValidationError as val_err:
            last_validation_error = val_err
        except json.JSONDecodeError:
            continue

    # 3. Attempt balanced-brace scanner extraction
    substring_candidates = extract_balanced_json_substrings(cleaned)
    for cand_str in substring_candidates:
        try:
            parsed = json.loads(cand_str)
            if isinstance(parsed, dict):
                if response_model is not None:
                    response_model.model_validate(parsed)
                return parsed
        except ValidationError as val_err:
            last_validation_error = val_err
        except json.JSONDecodeError:
            # 3b. Attempt safe trailing comma repair on balanced candidate
            try:
                repaired = _TRAILING_COMMA_RE.sub(r"\1", cand_str)
                parsed = json.loads(repaired)
                if isinstance(parsed, dict):
                    if response_model is not None:
                        response_model.model_validate(parsed)
                    logger.debug("Successfully recovered JSON object after repairing trailing comma")
                    return parsed
            except (json.JSONDecodeError, ValidationError) as rep_err:
                if isinstance(rep_err, ValidationError):
                    last_validation_error = rep_err
                continue

    # If any candidate was a valid JSON dict but failed schema validation, raise that error
    if last_validation_error is not None:
        raise last_validation_error

    # 4. Check for truncation
    if detect_truncation(cleaned):
        raise JsonTruncationError("model output appears truncated (unterminated JSON object or unclosed string)")

    raise StructuredOutputError("model response did not contain a valid JSON object")
