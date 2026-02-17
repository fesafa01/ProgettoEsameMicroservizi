"""Pydantic models for knowledge validation payloads."""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SourceDocument(BaseModel):
    """Source document metadata used for provenance tracking."""

    id: str
    title: str
    date: dt_date | None = None
    uri: str | None = None
    version: str | None = None


class KnowledgeEntity(BaseModel):
    """Single knowledge entity extracted from source material."""

    id: str
    name: str
    domain: str | None = None
    facts: list[str] = Field(default_factory=list)
    reliability: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: list[str] = Field(default_factory=list)
    updated_at: dt_date | None = None
    valid_from: dt_date | None = None
    valid_to: dt_date | None = None
    version: str | None = None
    status: str = "active"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_source(cls, data: Any) -> Any:
        """Support legacy `source` field by mapping it into provenance."""
        if isinstance(data, dict):
            source = data.get("source")
            provenance = data.get("provenance")
            if source and not provenance:
                data["provenance"] = [str(source)]
        return data


class KnowledgeRelation(BaseModel):
    """Relationship connecting two knowledge entities."""

    source: str
    type: str
    target: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class KnowledgeBase(BaseModel):
    """Knowledge snapshot produced by Agent 1."""

    knowledge_base_id: str = "kb-default"
    snapshot_id: str = "snapshot-unknown"
    reference_version: str | None = None
    created_at: datetime | None = None
    source_docs: list[SourceDocument] = Field(default_factory=list)
    entities: list[KnowledgeEntity] = Field(default_factory=list)
    relations: list[KnowledgeRelation] = Field(default_factory=list)


class ReferencePolicy(BaseModel):
    """Reference constraints used to validate knowledge."""

    min_valid_date: dt_date | None = None
    min_reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    required_domains: list[str] = Field(default_factory=list)
    prohibited_terms: list[str] = Field(default_factory=list)
    forbidden_statuses: list[str] = Field(default_factory=list)
    require_provenance: bool = True


class ValidationIssue(BaseModel):
    """Single validation issue found during checks."""

    code: str
    severity: str
    message: str
    entity_id: str | None = None
    relation_ref: str | None = None
    details: dict[str, Any] | None = None
    suggested_action: str | None = None


class ValidationReport(BaseModel):
    """Report produced after validating a knowledge base."""

    generated_at: datetime
    knowledge_base_id: str
    snapshot_id: str
    reference_version: str | None = None
    mode: str
    summary: dict[str, int]
    issues: list[ValidationIssue]
    clarification_questions: list[str]
    ai_report: str | None = None
