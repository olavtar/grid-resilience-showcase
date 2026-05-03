#!/usr/bin/env python3
# This project was developed with assistance from AI tools.

"""Cosmos Reason 2-8B detection validation harness."""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

import httpx
import yaml

DETECTION_PROMPT = (
    "You are a utility infrastructure monitoring AI. You are observing "
    "a frame from a fixed camera mounted on distribution grid infrastructure.\n\n"
    "Examine the image and answer: are any of the following conditions present?\n"
    "- Cracked, broken, or split crossarms\n"
    "- Damaged or missing insulators\n"
    "- Vegetation within 3 meters of conductors\n"
    "- Leaning or tilted poles\n"
    "- Missing hardware (bolts, clamps, guy wire attachments)\n"
    "- Visible corrosion on metal components\n"
    "- Animal nests or debris on equipment\n"
    "- Ice accumulation on conductors or equipment\n\n"
    "For each condition observed, respond with JSON:\n"
    "{\n"
    '  "findings": [\n'
    "    {\n"
    '      "defect_type": "cracked_crossarm",\n'
    '      "severity": "critical",\n'
    '      "confidence": 0.91,\n'
    '      "description": "...",\n'
    '      "recommended_action": "..."\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    'If no conditions are observed, return: {"findings": []}'
)


def run_detection(
    image_path: Path,
    vllm_url: str,
    model: str,
    client: httpx.Client,
) -> tuple[list[dict], float]:
    """Run a single image through Cosmos Reason and return findings + latency."""
    image_data = base64.b64encode(image_path.read_bytes()).decode()

    request_body = {
        "model": model,
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
        response = client.post(
            f"{vllm_url}/v1/chat/completions",
            json=request_body,
            timeout=60.0,
        )
        response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"    Request failed: {e}")
        return [], 0.0

    latency_ms = (time.monotonic() - start) * 1000

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed.get("findings", []), latency_ms
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"    Parse failed: {e}")
        raw = data.get("choices", [{}])[0].get("message", {}).get("content", "N/A")
        print(f"    Raw content: {raw[:200]}")
        return [], latency_ms


def evaluate_result(
    findings: list[dict],
    expected_finding: str | None,
) -> tuple[bool, str]:
    """Check if the detection result matches the expected outcome."""
    if expected_finding is None:
        if len(findings) == 0:
            return True, "correct — no findings expected, none returned"
        return False, f"false positive — expected none, got {len(findings)} findings"

    matching = [f for f in findings if f.get("defect_type") == expected_finding]
    if matching:
        conf = matching[0].get("confidence", 0)
        return True, f"correct — found {expected_finding} (confidence: {conf:.2f})"
    if findings:
        found_types = [f.get("defect_type") for f in findings]
        return False, f"wrong type — expected {expected_finding}, got {found_types}"
    return False, f"missed — expected {expected_finding}, got no findings"


def main() -> None:
    parser = argparse.ArgumentParser(description="Cosmos Reason detection validation")
    parser.add_argument("--vllm-url", default="http://localhost:8000")
    parser.add_argument("--model", default="nvidia/Cosmos-Reason2-8B")
    parser.add_argument("--image-dir", type=Path, default=Path("data/images"))
    parser.add_argument("--config", type=Path, default=Path("tools/cosmos-transfer/config.yaml"))
    parser.add_argument("--gate", type=float, default=0.90, help="Accuracy gate (0-1)")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    image_set = config.get("image_set", [])
    if not image_set:
        print("No images defined in config", file=sys.stderr)
        sys.exit(1)

    print("Cosmos Reason Detection Validation")
    print(f"  vLLM: {args.vllm_url}")
    print(f"  Model: {args.model}")
    print(f"  Images: {len(image_set)}")
    print(f"  Gate: {args.gate * 100:.0f}%")
    print("=" * 60)

    client = httpx.Client()
    correct = 0
    total = 0
    results = []

    for entry in image_set:
        filename = entry["filename"]
        camera_id = entry["camera_id"]
        expected = entry.get("expected_finding")

        # Check both base and augmented directories
        image_path = args.image_dir / "augmented" / f"augmented_{filename}"
        if not image_path.exists():
            image_path = args.image_dir / "base" / filename
        if not image_path.exists():
            image_path = args.image_dir / filename
        if not image_path.exists():
            print(f"\n[SKIP] {camera_id} / {filename} — image not found")
            continue

        print(f"\n[TEST] {camera_id} / {filename}")
        print(f"  Expected: {expected or 'no findings'}")

        findings, latency_ms = run_detection(image_path, args.vllm_url, args.model, client)
        passed, message = evaluate_result(findings, expected)

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {message} ({latency_ms:.0f}ms)")

        total += 1
        if passed:
            correct += 1
        results.append(
            {
                "camera_id": camera_id,
                "filename": filename,
                "expected": expected,
                "passed": passed,
                "message": message,
                "findings": findings,
                "latency_ms": latency_ms,
            }
        )

    print("\n" + "=" * 60)
    accuracy = correct / total if total > 0 else 0.0
    print(f"Results: {correct}/{total} correct ({accuracy * 100:.0f}%)")
    print(f"Gate: {args.gate * 100:.0f}%")

    if accuracy >= args.gate:
        print(f"PASSED — accuracy meets {args.gate * 100:.0f}% gate")
    else:
        print(f"FAILED — accuracy below {args.gate * 100:.0f}% gate")
        print("Consider iterating on the prompt or using hybrid YOLO + Cosmos Reason approach")
        sys.exit(1)

    # Write results JSON for review
    results_path = Path("tools/cosmos-validate/results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results: {results_path}")


if __name__ == "__main__":
    main()
