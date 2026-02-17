from kv.models import KnowledgeBase, KnowledgeEntity, ReferencePolicy
from kv.validator import validate


def test_validation_report_counts():
    knowledge = KnowledgeBase(
        knowledge_base_id="kb-test",
        snapshot_id="kb-test-001",
        source_docs=[{"id": "doc-1", "title": "Policy Manual", "date": "2025-01-01"}],
        entities=[
            KnowledgeEntity(
                id="ent-001",
                name="Policy A",
                domain="policy",
                facts=["Retention is 12 months"],
                reliability=0.5,
                provenance=["doc-1"],
                updated_at="2023-01-01",
            ),
            KnowledgeEntity(
                id="ent-002",
                name="Policy A",
                domain="policy",
                facts=["Retention is 24 months", "This statement is deprecated"],
                reliability=0.9,
                provenance=["doc-1"],
                updated_at="2025-01-01",
            ),
        ]
    )
    reference = ReferencePolicy(
        min_valid_date="2024-01-01",
        min_reliability=0.7,
        required_domains=["policy", "procedure"],
        prohibited_terms=["deprecated"],
        require_provenance=True,
    )

    report = validate(knowledge, reference)

    assert report.summary["total_entities"] == 2
    assert report.summary["duplicate_name_issues"] == 1
    assert report.summary["obsolete_issues"] == 1
    assert report.summary["conflicting_fact_issues"] == 1
    assert report.summary["prohibited_term_issues"] == 1
    assert report.summary["missing_required_domain_issues"] == 1
    assert report.summary["questions"] >= 1
    assert report.summary["issues_total"] >= 5
