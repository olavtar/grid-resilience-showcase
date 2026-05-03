#!/usr/bin/env python3
# This project was developed with assistance from AI tools.

"""Validate cuOpt 26.x open-source API schema with a minimal VRP problem."""

from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

CUOPT_DEFAULT_URL = "http://localhost:5000"

MINIMAL_VRP = {
    "cost_matrix_data": {
        "data": {
            "0": [
                0.0,
                5.2,
                8.1,
                3.4,
                5.2,
                0.0,
                6.7,
                7.3,
                8.1,
                6.7,
                0.0,
                4.5,
                3.4,
                7.3,
                4.5,
                0.0,
            ]
        }
    },
    "fleet_data": {
        "vehicle_ids": ["CREW-A", "CREW-B"],
        "vehicle_locations": [[0, 0], [0, 0]],
        "capacities": [[1, 1]],
        "vehicle_time_windows": [[0, 480], [0, 480]],
    },
    "task_data": {
        "task_ids": ["WO-001", "WO-002"],
        "task_locations": [1, 2],
        "demand": [[1, 1]],
        "task_time_windows": [[0, 480], [0, 480]],
        "service_times": [60, 90],
        "priorities": [10, 7],
    },
    "solver_config": {
        "time_limit": 5,
    },
}


def check_health(client: httpx.Client, url: str) -> bool:
    """Check cuOpt health endpoint."""
    try:
        resp = client.get(f"{url}/cuopt/health", timeout=10.0)
        print(f"Health check: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Response: {resp.json()}")
            return True
        print(f"  Unexpected status: {resp.status_code}")
        return False
    except httpx.RequestError as e:
        print(f"  Connection failed: {e}")
        return False


def submit_vrp(client: httpx.Client, url: str) -> dict | None:
    """Submit a minimal VRP problem to cuOpt."""
    print(f"\nSubmitting VRP problem to {url}/cuopt/request")
    print(f"  Vehicles: {len(MINIMAL_VRP['fleet_data']['vehicle_ids'])}")
    print(f"  Tasks: {len(MINIMAL_VRP['task_data']['task_ids'])}")
    print("  Cost matrix: 4x4")

    start = time.monotonic()
    try:
        resp = client.post(
            f"{url}/cuopt/request",
            json=MINIMAL_VRP,
            timeout=30.0,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        print(f"\nResponse: {resp.status_code} ({elapsed_ms:.0f}ms)")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Response keys: {list(data.keys())}")
            print(f"  Full response:\n{json.dumps(data, indent=2)}")
            return data
        else:
            print(f"  Error body: {resp.text}")
            return None
    except httpx.RequestError as e:
        print(f"  Request failed: {e}")
        return None


def validate_response(data: dict) -> bool:
    """Validate the cuOpt response structure."""
    print("\nValidating response schema...")
    checks = []

    if "response" in data:
        resp = data["response"]
        checks.append(("response key exists", True))

        if "solver_response" in resp:
            solver = resp["solver_response"]
            checks.append(("solver_response key exists", True))

            for key in ["status", "num_vehicles", "solution_cost"]:
                present = key in solver
                checks.append((f"solver_response.{key}", present))

            if "vehicle_data" in solver:
                checks.append(("vehicle_data key exists", True))
                vdata = solver["vehicle_data"]
                for vid, routes in vdata.items():
                    checks.append((f"vehicle {vid} has route", "route" in routes))
            else:
                checks.append(("vehicle_data key exists", False))
        else:
            checks.append(("solver_response key exists", False))
    else:
        checks.append(("response key exists", False))

    passed = all(ok for _, ok in checks)
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\nOverall: {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate cuOpt API schema")
    parser.add_argument("--url", default=CUOPT_DEFAULT_URL)
    args = parser.parse_args()

    print(f"cuOpt API Validation — {args.url}")
    print("=" * 50)

    client = httpx.Client()

    if not check_health(client, args.url):
        print("\ncuOpt is not reachable. Ensure the container is running:")
        print("  podman run -p 5000:5000 nvidia/cuopt:26.06-cuda12.9-py3.13")
        sys.exit(1)

    result = submit_vrp(client, args.url)
    if result is None:
        print("\nVRP submission failed")
        sys.exit(1)

    if not validate_response(result):
        print("\nResponse schema does not match expected structure.")
        print("The cuOpt 26.x API may have changed — review the response above")
        print("and update dispatch_optimizer/optimizer.py accordingly.")
        sys.exit(1)

    print("\ncuOpt API validation passed — schema is compatible")


if __name__ == "__main__":
    main()
