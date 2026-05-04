# This project was developed with assistance from AI tools.

"""Detection logic — calls Cosmos Reason 2-8B via vLLM."""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path

import httpx
import structlog

from defect_detector.prompt import DETECTION_PROMPT
from defect_detector.settings import DefectDetectorSettings
from grid_common.events import DefectFinding

logger = structlog.get_logger()

DEFECT_TYPE_ALIASES: dict[str, str] = {
    "ice_accumulation_on_conductors": "ice_accumulation",
    "ice_accumulation_on_equipment": "ice_accumulation",
    "ice_loading_on_conductors": "ice_loading",
    "vegetation_encroachment_on_conductors": "vegetation_encroachment",
    "cracked_wooden_crossarm": "cracked_crossarm",
    "broken_crossarm": "cracked_crossarm",
}


def _normalize_defect_type(raw: str) -> str:
    return DEFECT_TYPE_ALIASES.get(raw, raw)


async def analyze_frame(
    image_url: str,
    client: httpx.AsyncClient,
    settings: DefectDetectorSettings,
) -> tuple[list[DefectFinding], float]:
    """Send image to Cosmos Reason via vLLM and parse findings."""
    image_path = Path(image_url)
    if not image_path.exists():
        logger.warning("image_not_found", path=image_url)
        return [], 0.0

    image_data = base64.b64encode(image_path.read_bytes()).decode()

    request_body = {
        "model": settings.vllm_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"},
                    },
                    {"type": "text", "text": DETECTION_PROMPT},
                ],
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.1,
    }

    start = time.monotonic()
    try:
        response = await client.post(
            f"{settings.vllm_base_url}/v1/chat/completions",
            json=request_body,
            timeout=settings.vllm_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.RequestError as e:
        logger.error("vllm_request_failed", error=str(e))
        return [], 0.0
    except httpx.HTTPStatusError as e:
        logger.error("vllm_http_error", status=e.response.status_code)
        return [], 0.0

    latency_ms = (time.monotonic() - start) * 1000

    try:
        data = response.json()
        message = data["choices"][0]["message"]
        raw_text = message.get("content") or message.get("reasoning") or ""
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match is None:
            logger.warning("vllm_no_json_in_response", text=raw_text[:200])
            return [], latency_ms
        parsed = json.loads(json_match.group())
        raw_findings = parsed.get("findings", [])
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        logger.warning("vllm_response_parse_error", error=str(e))
        return [], latency_ms

    severity_map = {"minor": "warning", "low": "info", "medium": "major", "high": "critical"}
    valid_severities = {"info", "warning", "major", "critical"}

    findings = []
    for f in raw_findings:
        confidence = f.get("confidence", 0.0)
        if confidence < settings.confidence_threshold:
            continue
        defect_type = _normalize_defect_type(f.get("defect_type", "unknown"))
        raw_severity = f.get("severity", "info")
        severity = severity_map.get(raw_severity, raw_severity)
        if severity not in valid_severities:
            severity = "major"
        findings.append(
            DefectFinding(
                defect_type=defect_type,
                severity=severity,
                confidence=confidence,
                description=f.get("description", ""),
                recommended_action=f.get("recommended_action", f.get("action", "")),
            )
        )

    return findings, latency_ms
