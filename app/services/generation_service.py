import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.llm_factory import get_llm

llm = get_llm()


def invoke_llm_with_retry(prompt: str, *, system: bool = True) -> str:
    last_error: Exception | None = None
    for attempt in range(settings.LLM_RETRY_COUNT + 1):
        try:
            message = SystemMessage(content=prompt) if system else HumanMessage(content=prompt)
            response = llm.invoke([message])
            return str(response.content).strip()
        except Exception as exc:  # pragma: no cover - network/runtime resilience
            last_error = exc
            if attempt >= settings.LLM_RETRY_COUNT:
                break
            time.sleep(settings.LLM_RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise RuntimeError(f"LLM invocation failed after retries: {last_error}")


def build_general_prompt(query: str) -> str:
    return f"""
You are PrivAI, a friendly and professional enterprise AI assistant.
The user is asking a general conversational query, not a document-grounded request.

Guidelines:
- Respond naturally and helpfully.
- Keep the response concise and clear.
- Use markdown when useful.
- Do not mention retrieval context, chunks, or validation metadata.

User Query: {query}
"""


def build_grounded_qa_prompt(query: str, context: str) -> str:
    return f"""
You are PrivAI, a strict enterprise assistant.
Answer only using the provided context.
If information is not present, respond exactly: "Information not found in provided context."
Do not infer, invent, or add external facts.
Format the answer using markdown headings and bullet points.
Use concise sections suitable for an enterprise report.
Do not include raw metadata such as JSON, sources list, validation lines, or confidence text.

User Query: {query}
Context:
{context}
"""


def build_summary_prompt(context: str) -> str:
    return f"""
You are a strict summarization assistant.
Use only the provided context.
If a section cannot be found, set it to "Not present in document".
Format output content for enterprise readability.
Do not add metadata fields beyond the required JSON structure.

Context:
{context}

Return only valid JSON with this schema:
{{
  "overview": ["..."],
  "key_points": ["..."],
  "highlights": ["..."]
}}
"""


def build_extraction_prompt(context: str, task_type: str) -> tuple[str, list[str]]:
    if task_type == "meeting":
        schema = """{
  "meeting_summary": ["exact statement from context"],
  "key_decisions": ["exact statement from context"],
  "action_items": ["exact statement from context"],
  "risks_blockers": ["exact statement from context"]
}"""
        required_keys = ["meeting_summary", "key_decisions", "action_items", "risks_blockers"]
    else:
        schema = """{
  "key_clauses": ["exact statement from context"],
  "obligations": ["exact statement from context"],
  "risks": ["exact statement from context"],
  "termination_terms": ["exact statement from context"]
}"""
        required_keys = ["key_clauses", "obligations", "risks", "termination_terms"]

    prompt = f"""
You are a strict enterprise contract and compliance extraction assistant.
Extract only information explicitly present in the provided context.
Never infer or invent clauses, risks, obligations, or terms.
When a section is absent, return exactly "Not present in document" for that section.
When possible, use exact text spans copied from the context.
Do not include any extra fields, markdown wrappers, or metadata.

Context:
{context}

Return only valid JSON matching this schema:
{schema}
"""
    return prompt, required_keys


def build_validation_prompt(query: str, context: str, answer: str, task_type: str) -> str:
    structure_rule = ""
    if task_type in {"analyze", "meeting", "summarize"}:
        structure_rule = "Also verify that the answer follows required structured extraction sections and avoids hallucinated sections."

    return f"""
You are a grounding validator.
Check whether the answer is fully supported by provided context and contains no hallucinations.
{structure_rule}

Query: {query}
Context:
{context}
Answer:
{answer}

Return exactly one line:
APPROVED: <reason>
or
REJECTED: <reason>
"""


def build_structured_response(structured: dict[str, list[str]]) -> str:
    lines: list[str] = []
    for key, values in structured.items():
        title = key.replace("_", " ").title()
        lines.append(f"{title}:")
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    return "\n".join(lines).strip()
