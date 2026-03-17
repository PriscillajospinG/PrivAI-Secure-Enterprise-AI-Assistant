import argparse
import json
import pathlib
import sys

import requests


def assert_status(response: requests.Response, expected: int, label: str):
    if response.status_code != expected:
        raise RuntimeError(f"{label} failed: expected {expected}, got {response.status_code}, body={response.text[:400]}")


def run(base_url: str, sample_file: str):
    health = requests.get(f"{base_url}/health", timeout=15)
    assert_status(health, 200, "health")

    with open(sample_file, "rb") as handle:
        upload = requests.post(f"{base_url}/upload", files={"files": handle}, timeout=120)
    assert_status(upload, 200, "upload")

    tasks = ["chat", "search", "summarize", "analyze", "meeting"]
    for task in tasks:
        query = requests.post(
            f"{base_url}/query",
            json={"query": "What is the leave policy?", "task_type": task, "top_k": 4},
            timeout=180,
        )
        assert_status(query, 200, f"query:{task}")
        body = query.json()
        if not body.get("success"):
            raise RuntimeError(f"query:{task} returned success=false")
        if not body.get("result", {}).get("response"):
            raise RuntimeError(f"query:{task} did not return response")

    print(json.dumps({"status": "ok", "tested_tasks": tasks}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="PrivAI API smoke tests")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--sample-file", default="data/docs/hr.txt")
    args = parser.parse_args()

    sample = pathlib.Path(args.sample_file)
    if not sample.exists():
        print(f"Sample file not found: {sample}", file=sys.stderr)
        sys.exit(1)

    run(args.base_url, str(sample))


if __name__ == "__main__":
    main()
