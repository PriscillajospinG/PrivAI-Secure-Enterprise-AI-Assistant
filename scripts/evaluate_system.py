import argparse
import json
import re
import time
from pathlib import Path

import httpx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text or "")]


def _token_prf1(prediction: str, reference: str) -> tuple[float, float, float]:
    pred_tokens = _tokenize(prediction)
    ref_tokens = _tokenize(reference)
    if not pred_tokens and not ref_tokens:
        return 1.0, 1.0, 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0, 0.0, 0.0

    pred_counts: dict[str, int] = {}
    ref_counts: dict[str, int] = {}
    for token in pred_tokens:
        pred_counts[token] = pred_counts.get(token, 0) + 1
    for token in ref_tokens:
        ref_counts[token] = ref_counts.get(token, 0) + 1

    overlap = sum(min(pred_counts[token], ref_counts.get(token, 0)) for token in pred_counts)
    precision = overlap / max(len(pred_tokens), 1)
    recall = overlap / max(len(ref_tokens), 1)
    if precision + recall == 0:
        return precision, recall, 0.0
    f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def _load_dataset(path: Path) -> list[dict]:
    if path.suffix.lower() == ".jsonl":
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
        if isinstance(payload, list):
            return payload
        raise ValueError("Dataset JSON must be a list of records.")


def _call_query_api(base_url: str, query: str, task_type: str) -> tuple[dict, float]:
    request_body = {"query": query, "task_type": task_type, "top_k": 4}
    start = time.perf_counter()
    with httpx.Client(timeout=90.0) as client:
        response = client.post(f"{base_url}/query", json=request_body)
        response.raise_for_status()
        payload = response.json()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return payload, elapsed_ms


def evaluate(base_url: str, dataset_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = _load_dataset(dataset_path)

    y_true: list[int] = []
    y_pred: list[int] = []
    token_precisions: list[float] = []
    token_recalls: list[float] = []
    token_f1s: list[float] = []
    exact_matches: list[int] = []
    latencies_ms: list[float] = []
    detailed_rows: list[dict] = []

    for idx, row in enumerate(dataset):
        query = row.get("query", "")
        if not query:
            continue

        task_type = row.get("task_type", "chat")
        expected_answer = row.get("expected_answer", "")
        expected_grounded = int(bool(row.get("expected_grounded", 1)))

        payload, elapsed_ms = _call_query_api(base_url, query, task_type)
        result = payload.get("result", {})
        prediction = str(result.get("response", ""))
        approved = int(bool(result.get("approved", False)))

        y_true.append(expected_grounded)
        y_pred.append(approved)

        precision, recall, f1 = _token_prf1(prediction, expected_answer)
        token_precisions.append(precision)
        token_recalls.append(recall)
        token_f1s.append(f1)

        exact_match = int(prediction.strip().lower() == expected_answer.strip().lower())
        exact_matches.append(exact_match)
        latencies_ms.append(elapsed_ms)

        detailed_rows.append(
            {
                "index": idx,
                "query": query,
                "task_type": task_type,
                "expected_grounded": expected_grounded,
                "predicted_grounded": approved,
                "token_precision": round(precision, 4),
                "token_recall": round(recall, 4),
                "token_f1": round(f1, 4),
                "exact_match": exact_match,
                "response_time_ms": round(elapsed_ms, 2),
            }
        )

    if not y_true:
        raise RuntimeError("No valid evaluation rows found in dataset.")

    metrics = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "exact_match": round(sum(exact_matches) / len(exact_matches), 4),
        "token_precision": round(sum(token_precisions) / len(token_precisions), 4),
        "token_recall": round(sum(token_recalls) / len(token_recalls), 4),
        "token_f1": round(sum(token_f1s) / len(token_f1s), 4),
        "response_time_ms_avg": round(sum(latencies_ms) / len(latencies_ms), 2),
        "response_time_ms_p95": round(sorted(latencies_ms)[int(len(latencies_ms) * 0.95) - 1], 2) if len(latencies_ms) > 1 else round(latencies_ms[0], 2),
        "samples": len(y_true),
    }

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Not Grounded", "Grounded"])
    fig, ax = plt.subplots(figsize=(5, 4))
    disp.plot(ax=ax, colorbar=False)
    ax.set_title("Grounding Confusion Matrix")
    fig.tight_layout()
    fig.savefig(output_dir / "confusion_matrix.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(range(1, len(latencies_ms) + 1), latencies_ms, marker="o", linewidth=1)
    ax.set_title("Response Time Per Query")
    ax.set_xlabel("Query #")
    ax.set_ylabel("Latency (ms)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "response_times.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    metric_names = ["Accuracy", "Precision", "Recall", "F1"]
    metric_values = [metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["f1_score"]]
    ax.bar(metric_names, metric_values)
    ax.set_ylim(0, 1)
    ax.set_title("Evaluation Metrics")
    fig.tight_layout()
    fig.savefig(output_dir / "metrics_bar_chart.png", dpi=160)
    plt.close(fig)

    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)

    with (output_dir / "detailed_results.json").open("w", encoding="utf-8") as handle:
        json.dump(detailed_rows, handle, indent=2)

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate PrivAI with quality and latency metrics.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of running PrivAI backend")
    parser.add_argument("--dataset", default="data/eval/sample_eval.jsonl", help="Path to evaluation dataset (.json/.jsonl)")
    parser.add_argument("--output-dir", default="reports/evaluation", help="Directory for reports and charts")
    args = parser.parse_args()

    metrics = evaluate(args.base_url, Path(args.dataset), Path(args.output_dir))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
