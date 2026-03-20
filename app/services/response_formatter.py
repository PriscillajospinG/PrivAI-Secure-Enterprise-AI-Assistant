import re
from typing import Any


def _section_title_from_query(query: str) -> str:
    cleaned = " ".join(query.strip().split())
    if not cleaned:
        return "Enterprise Knowledge Response"
    return cleaned[:80]


def _clean_model_text(text: str) -> str:
    """Strip duplicated metadata lines from LLM output before rendering."""
    if not text:
        return ""

    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines: list[str] = []
    for line in lines:
        normalized = line.strip().lower()
        if normalized.startswith("sources:"):
            continue
        if normalized.startswith("validation:"):
            continue
        if normalized.startswith("confidence:"):
            continue
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items if items else ["Not present in document"]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return ["Not present in document"]


def _title_case(name: str) -> str:
    return name.replace("_", " ").strip().title()


def _format_structured_markdown(query: str, structured_output: dict[str, Any]) -> str:
    lines: list[str] = [f"## {_section_title_from_query(query)}", "", "### Answer", ""]
    for key, raw_value in structured_output.items():
        lines.append(f"#### {_title_case(key)}")
        for item in _as_list(raw_value):
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_text_markdown(query: str, text: str) -> str:
    cleaned = _clean_model_text(text)
    if not cleaned:
        cleaned = "Information not found in provided context."

    blocks = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    lines: list[str] = [f"## {_section_title_from_query(query)}", "", "### Answer", ""]

    for block in blocks:
        if block.startswith("- ") or block.startswith("* "):
            lines.append(block)
            lines.append("")
            continue

        block_lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(block_lines) > 1:
            for line in block_lines:
                if line.startswith("- ") or line.startswith("* "):
                    lines.append(line)
                else:
                    lines.append(f"- {line}")
            lines.append("")
        else:
            lines.append(block)
            lines.append("")

    return "\n".join(lines).strip()


def format_validation_status(approved: bool) -> str:
    return "✔ grounded in context" if approved else "✖ hallucination detected"


def format_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate and keep only relevant, known sources."""
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int | None]] = set()

    sorted_sources = sorted(
        sources,
        key=lambda source: (source.get("score") is None, -(float(source.get("score") or 0.0))),
    )

    for source in sorted_sources:
        name = str(source.get("source", "")).strip()
        if not name or name.lower() == "unknown":
            continue

        chunk_id = str(source.get("chunk_id", "")).strip()
        page_number = source.get("page_number")
        if not isinstance(page_number, int):
            page_number = None

        key = (name, chunk_id, page_number)
        if key in seen:
            continue
        seen.add(key)

        deduped.append(
            {
                "source": name,
                "chunk_id": chunk_id,
                "page_number": page_number,
                "score": source.get("score"),
                "snippet": str(source.get("snippet", "")).strip(),
            }
        )

    return deduped


def format_answer(query: str, response: str, structured_output: dict[str, Any] | None) -> str:
    if structured_output and isinstance(structured_output, dict):
        return _format_structured_markdown(query, structured_output)
    return _format_text_markdown(query, response)
