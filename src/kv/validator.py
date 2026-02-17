"""AI-based validation logic for knowledge bases against reference policies."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import UTC, datetime

from kv.llm import generate_validation_text
from kv.models import KnowledgeBase, ReferencePolicy, ValidationIssue, ValidationReport


def _extract_month_values(facts: list[str]) -> set[int]:
    """Extract month values from fact strings."""
    values: set[int] = set()
    for fact in facts:
        for match in re.findall(r"\b(\d{1,3})\s*months?\b", fact, flags=re.IGNORECASE):
            values.add(int(match))
    return values


def _build_clarification_questions(issues: list[ValidationIssue]) -> list[str]:
    """Generate concise clarification questions from issues."""
    questions: list[str] = []
    for issue in issues:
        if issue.code == "CONFLICTING_FACTS":
            questions.append(
                "Qual e il valore corretto tra i fatti in conflitto e quale documento lo conferma?"
            )
        elif issue.code == "MISSING_PROVENANCE":
            questions.append(
                "Puoi indicare il documento sorgente per le entita senza provenance?"
            )
        elif issue.code == "MISSING_REQUIRED_DOMAIN":
            questions.append("Quale fonte copre i domini richiesti ma assenti nello snapshot?")
        elif issue.code == "LOW_RELIABILITY":
            questions.append(
                "Le entita con reliability bassa possono essere confermate con fonti aggiuntive?"
            )
        elif issue.code == "RELATIONSHIP_CYCLE":
            questions.append(
                "La dipendenza ciclica e intenzionale oppure uno dei due legami va corretto?"
            )
    return list(dict.fromkeys(questions))


def validate(knowledge: KnowledgeBase, reference: ReferencePolicy) -> ValidationReport:
    """Validate a knowledge base with deterministic checks and optional AI synthesis."""
    issues: list[ValidationIssue] = []
    entities = knowledge.entities
    source_doc_ids = {doc.id for doc in knowledge.source_docs}

    names_to_ids: dict[str, list[str]] = defaultdict(list)
    names_to_months: dict[str, set[int]] = defaultdict(set)
    present_domains: set[str] = set()
    duplicate_count = 0
    obsolete_count = 0
    low_reliability_count = 0
    prohibited_term_count = 0
    missing_provenance_count = 0
    conflicting_fact_count = 0
    missing_domain_count = 0

    for entity in entities:
        normalized_name = entity.name.strip().lower()
        names_to_ids[normalized_name].append(entity.id)
        names_to_months[normalized_name].update(_extract_month_values(entity.facts))

        if entity.domain:
            present_domains.add(entity.domain)
        else:
            missing_domain_count += 1
            issues.append(
                ValidationIssue(
                    code="MISSING_DOMAIN",
                    severity="high",
                    message=f"Entity '{entity.name}' has no domain.",
                    entity_id=entity.id,
                    suggested_action="Set the entity domain to a valid taxonomy value.",
                )
            )

        if reference.min_valid_date and entity.updated_at and entity.updated_at < reference.min_valid_date:
            obsolete_count += 1
            issues.append(
                ValidationIssue(
                    code="OBSOLETE_ENTITY",
                    severity="medium",
                    message=(
                        f"Entity '{entity.name}' is obsolete: updated_at={entity.updated_at.isoformat()} "
                        f"is older than min_valid_date={reference.min_valid_date.isoformat()}."
                    ),
                    entity_id=entity.id,
                    details={
                        "updated_at": entity.updated_at.isoformat(),
                        "min_valid_date": reference.min_valid_date.isoformat(),
                    },
                    suggested_action="Refresh this entity from a newer document.",
                )
            )

        if entity.reliability is not None and entity.reliability < reference.min_reliability:
            low_reliability_count += 1
            issues.append(
                ValidationIssue(
                    code="LOW_RELIABILITY",
                    severity="medium",
                    message=(
                        f"Entity '{entity.name}' reliability {entity.reliability:.2f} is below "
                        f"threshold {reference.min_reliability:.2f}."
                    ),
                    entity_id=entity.id,
                    details={
                        "reliability": entity.reliability,
                        "min_reliability": reference.min_reliability,
                    },
                    suggested_action="Increase confidence by linking stronger evidence.",
                )
            )

        if reference.require_provenance:
            if not entity.provenance:
                missing_provenance_count += 1
                issues.append(
                    ValidationIssue(
                        code="MISSING_PROVENANCE",
                        severity="high",
                        message=f"Entity '{entity.name}' has no provenance.",
                        entity_id=entity.id,
                        suggested_action="Attach one or more source document IDs to provenance.",
                    )
                )
            else:
                unknown_sources = [doc_id for doc_id in entity.provenance if doc_id not in source_doc_ids]
                if unknown_sources:
                    missing_provenance_count += 1
                    issues.append(
                        ValidationIssue(
                            code="UNKNOWN_PROVENANCE_SOURCE",
                            severity="high",
                            message=f"Entity '{entity.name}' references unknown source docs.",
                            entity_id=entity.id,
                            details={"unknown_sources": unknown_sources},
                            suggested_action="Add missing source_docs metadata or fix provenance IDs.",
                        )
                    )

        if entity.status in reference.forbidden_statuses:
            issues.append(
                ValidationIssue(
                    code="FORBIDDEN_STATUS",
                    severity="medium",
                    message=f"Entity '{entity.name}' uses forbidden status '{entity.status}'.",
                    entity_id=entity.id,
                    suggested_action="Use an allowed status value for active knowledge.",
                )
            )

        fact_text = " ".join(entity.facts).lower()
        for term in reference.prohibited_terms:
            if term.lower() in fact_text:
                prohibited_term_count += 1
                issues.append(
                    ValidationIssue(
                        code="PROHIBITED_TERM",
                        severity="high",
                        message=f"Entity '{entity.name}' contains prohibited term '{term}'.",
                        entity_id=entity.id,
                        details={"term": term},
                        suggested_action="Remove or replace prohibited language.",
                    )
                )

        own_month_values = _extract_month_values(entity.facts)
        if len(own_month_values) > 1:
            conflicting_fact_count += 1
            issues.append(
                ValidationIssue(
                    code="CONFLICTING_FACTS",
                    severity="high",
                    message=f"Entity '{entity.name}' has conflicting month values in facts.",
                    entity_id=entity.id,
                    details={"month_values": sorted(own_month_values)},
                    suggested_action="Keep one canonical fact and archive obsolete statements.",
                )
            )

    for normalized_name, ids in names_to_ids.items():
        if len(set(ids)) > 1:
            duplicate_count += 1
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_ENTITY_NAME",
                    severity="high",
                    message=f"Duplicate entity name '{normalized_name}' appears with multiple IDs.",
                    details={"entity_ids": sorted(set(ids))},
                    suggested_action="Merge duplicates or rename entities clearly.",
                )
            )

    for normalized_name, month_values in names_to_months.items():
        if len(month_values) > 1:
            conflicting_fact_count += 1
            issues.append(
                ValidationIssue(
                    code="CONFLICTING_FACTS",
                    severity="high",
                    message=f"Conflicting retention values found for '{normalized_name}'.",
                    details={"month_values": sorted(month_values)},
                    suggested_action="Define one authoritative value and deprecate the rest.",
                )
            )

    for required_domain in reference.required_domains:
        if required_domain not in present_domains:
            issues.append(
                ValidationIssue(
                    code="MISSING_REQUIRED_DOMAIN",
                    severity="high",
                    message=f"Required domain '{required_domain}' is missing.",
                    details={"required_domain": required_domain},
                    suggested_action="Add at least one entity for each required domain.",
                )
            )

    cycle_count = 0
    edges = {
        (relation.source, relation.target)
        for relation in knowledge.relations
        if relation.type in {"depends_on", "requires", "parent_of"}
    }
    for source, target in sorted(edges):
        if (target, source) in edges and source < target:
            cycle_count += 1
            issues.append(
                ValidationIssue(
                    code="RELATIONSHIP_CYCLE",
                    severity="high",
                    message=f"Cyclic relationship detected between '{source}' and '{target}'.",
                    relation_ref=f"{source}->{target}",
                    suggested_action="Break the cycle by removing or changing one dependency.",
                )
            )

    summary = Counter(issue.code for issue in issues)
    clarification_questions = _build_clarification_questions(issues)
    summary.update({"questions": len(clarification_questions)})

    ai_report: str | None = None
    mode = "deterministic"
    try:
        ai_report = generate_validation_text(
            knowledge.model_dump(mode="json"), reference.model_dump(mode="json")
        )
        mode = "deterministic_and_ai"
    except RuntimeError:
        ai_report = None

    return ValidationReport(
        generated_at=datetime.now(UTC),
        knowledge_base_id=knowledge.knowledge_base_id,
        snapshot_id=knowledge.snapshot_id,
        reference_version=knowledge.reference_version,
        mode=mode,
        summary={
            "total_entities": len(entities),
            "issues_total": len(issues),
            "duplicate_name_issues": duplicate_count,
            "obsolete_issues": obsolete_count,
            "low_reliability_issues": low_reliability_count,
            "missing_provenance_issues": missing_provenance_count,
            "missing_domain_issues": missing_domain_count,
            "prohibited_term_issues": prohibited_term_count,
            "conflicting_fact_issues": conflicting_fact_count,
            "relationship_cycle_issues": cycle_count,
            "missing_required_domain_issues": sum(
                1 for issue in issues if issue.code == "MISSING_REQUIRED_DOMAIN"
            ),
            "questions": len(clarification_questions),
        },
        issues=issues,
        clarification_questions=clarification_questions,
        ai_report=ai_report,
    )
