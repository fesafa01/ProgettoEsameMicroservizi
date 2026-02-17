"""File-based storage helpers for the Knowledge Validator service."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from kv.models import KnowledgeBase, KnowledgeEntity, ReferencePolicy, SourceDocument

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
EXAMPLES_DIR = DATA_DIR / "examples"
AGENT1_PATH = DATA_DIR / "agent1_output.json"
REFERENCE_PATH = DATA_DIR / "reference.json"
REPORT_PATH = DATA_DIR / "validation_report.json"
HISTORY_PATH = DATA_DIR / "history.json"

DEFAULT_KB = KnowledgeBase(
    knowledge_base_id="kb-demo",
    snapshot_id="kb-demo-2026-02-16-001",
    reference_version="v1",
    created_at=datetime.fromisoformat("2026-02-16T10:00:00"),
    source_docs=[
        SourceDocument(
            id="doc-policy-001",
            title="Policy Manual v2",
            date=date.fromisoformat("2025-06-10"),
            version="2.0",
        ),
        SourceDocument(
            id="doc-sec-001",
            title="Security Runbook",
            date=date.fromisoformat("2024-12-01"),
            version="1.4",
        ),
    ],
    entities=[
        KnowledgeEntity(
            id="ent-001",
            name="Data Retention Policy",
            domain="policy",
            facts=[
                "Retention period is 24 months",
                "Applies to customer data",
            ],
            reliability=0.82,
            provenance=["doc-policy-001"],
            updated_at=date.fromisoformat("2025-06-10"),
            status="active",
        ),
        KnowledgeEntity(
            id="ent-002",
            name="Incident Response Procedure",
            domain="procedure",
            facts=[
                "Notify DPO within 72 hours",
                "Escalate severity 1 incidents immediately",
            ],
            reliability=0.9,
            provenance=["doc-sec-001"],
            updated_at=date.fromisoformat("2024-12-01"),
            status="active",
        ),
    ],
    relations=[
        {
            "source": "ent-002",
            "type": "implements",
            "target": "ent-001",
            "confidence": 0.8,
        }
    ],
)

DEFAULT_REFERENCE = ReferencePolicy(
    min_valid_date=date(2024, 1, 1),
    min_reliability=0.7,
    required_domains=["policy", "procedure"],
    prohibited_terms=["deprecated", "obsolete"],
    forbidden_statuses=["deprecated"],
    require_provenance=True,
)


def ensure_data_files() -> None:
    """Create data directory and default JSON files if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    if not AGENT1_PATH.exists():
        AGENT1_PATH.write_text(
            json.dumps(DEFAULT_KB.model_dump(mode="json"), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
    if not REFERENCE_PATH.exists():
        REFERENCE_PATH.write_text(
            json.dumps(DEFAULT_REFERENCE.model_dump(mode="json"), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text(
            json.dumps({"runs": []}, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read a JSON file and return its contents."""
    ensure_data_files()
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON file with pretty-printed formatting."""
    ensure_data_files()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def list_examples() -> list[str]:
    """List available JSON examples in the examples folder."""
    ensure_data_files()
    return sorted(path.name for path in EXAMPLES_DIR.glob("*.json") if path.is_file())


def load_example_data(name: str) -> dict[str, Any]:
    """Load one example by filename and return parsed JSON content."""
    ensure_data_files()
    if "/" in name or "\\" in name:
        raise ValueError("Invalid example name")
    example_path = EXAMPLES_DIR / name
    if not example_path.exists() or not example_path.is_file():
        raise FileNotFoundError(name)
    return json.loads(example_path.read_text(encoding="utf-8"))
