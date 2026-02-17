"""API routes for the Knowledge Validator service."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from kv.models import KnowledgeBase, ReferencePolicy, ValidationReport
from kv.storage import (
    AGENT1_PATH,
    HISTORY_PATH,
    REFERENCE_PATH,
    REPORT_PATH,
    load_example_data,
    list_examples,
    read_json,
    write_json,
)
from kv.validator import validate

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}


@router.get("/knowledge", response_model=KnowledgeBase)
def get_knowledge() -> KnowledgeBase:
    """Return the simulated Agent 1 knowledge base."""
    data = read_json(AGENT1_PATH)
    return KnowledgeBase.model_validate(data)


@router.put("/knowledge", response_model=KnowledgeBase)
def put_knowledge(payload: KnowledgeBase) -> KnowledgeBase:
    """Replace the stored knowledge base."""
    write_json(AGENT1_PATH, payload.model_dump(mode="json"))
    return payload


@router.get("/reference", response_model=ReferencePolicy)
def get_reference() -> ReferencePolicy:
    """Return the reference policy set."""
    data = read_json(REFERENCE_PATH)
    return ReferencePolicy.model_validate(data)


@router.put("/reference", response_model=ReferencePolicy)
def put_reference(payload: ReferencePolicy) -> ReferencePolicy:
    """Replace the stored reference policy set."""
    write_json(REFERENCE_PATH, payload.model_dump(mode="json"))
    return payload


@router.post("/validate", response_model=ValidationReport)
def run_validation() -> ValidationReport:
    """Run validation and persist the report."""
    knowledge = KnowledgeBase.model_validate(read_json(AGENT1_PATH))
    reference = ReferencePolicy.model_validate(read_json(REFERENCE_PATH))
    report = validate(knowledge, reference)
    write_json(REPORT_PATH, report.model_dump(mode="json"))
    _append_history(knowledge, report)
    return report


@router.post("/validate-text")
def run_validation_text() -> dict[str, str]:
    """Run validation and return the AI report as plain text."""
    knowledge = KnowledgeBase.model_validate(read_json(AGENT1_PATH))
    reference = ReferencePolicy.model_validate(read_json(REFERENCE_PATH))
    report = validate(knowledge, reference)
    write_json(REPORT_PATH, report.model_dump(mode="json"))
    _append_history(knowledge, report)
    return {"report": report.ai_report or ""}


@router.get("/validation-report", response_model=ValidationReport)
def get_validation_report() -> ValidationReport:
    """Return the latest validation report, generating one if missing."""
    if not REPORT_PATH.exists():
        knowledge = KnowledgeBase.model_validate(read_json(AGENT1_PATH))
        reference = ReferencePolicy.model_validate(read_json(REFERENCE_PATH))
        report = validate(knowledge, reference)
        write_json(REPORT_PATH, report.model_dump(mode="json"))
        _append_history(knowledge, report)
        return report
    data = read_json(REPORT_PATH)
    return ValidationReport.model_validate(data)


@router.get("/examples")
def get_examples() -> dict[str, list[str]]:
    """List available validation examples."""
    return {"examples": list_examples()}


@router.post("/load-example")
def load_example(name: str) -> dict[str, str]:
    """Load one named example into the active knowledge snapshot."""
    try:
        payload = load_example_data(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Example not found: {exc}") from exc

    snapshot = KnowledgeBase.model_validate(payload)
    write_json(AGENT1_PATH, snapshot.model_dump(mode="json"))
    return {
        "status": "loaded",
        "example": name,
        "snapshot_id": snapshot.snapshot_id,
    }


@router.get("/history")
def get_history() -> dict[str, list[dict[str, str | int | None]]]:
    """Return validation history metadata."""
    data = read_json(HISTORY_PATH, default={"runs": []})
    runs = data.get("runs", [])
    if not isinstance(runs, list):
        runs = []
    return {"runs": runs}


def _append_history(knowledge: KnowledgeBase, report: ValidationReport) -> None:
    """Append one validation run summary to local history."""
    history = read_json(HISTORY_PATH, default={"runs": []})
    runs = history.get("runs", [])
    if not isinstance(runs, list):
        runs = []
    runs.append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "knowledge_base_id": knowledge.knowledge_base_id,
            "snapshot_id": knowledge.snapshot_id,
            "reference_version": knowledge.reference_version,
            "mode": report.mode,
            "issues_total": report.summary.get("issues_total"),
            "questions": report.summary.get("questions"),
        }
    )
    history["runs"] = runs[-100:]
    write_json(HISTORY_PATH, history)
