# Knowledge Validator (Agent 2)

The Knowledge Validator (KV) is a FastAPI service that validates structured knowledge snapshots extracted by Agent 1.
It combines deterministic checks (repeatable and testable) with optional Groq AI synthesis (`ai_report`).

## Current Scope

- Accepts a strict Agent 1 snapshot schema with metadata and relations
- Runs deterministic validation checks and produces structured `issues[]`
- Optionally calls Groq to generate a human-readable report (`ai_report`)
- Stores snapshots, reference policy, reports, and history in `data/`
- Ships a broad example suite in `data/examples/` for demo and testing

## Agent 1 Snapshot Schema (Implemented)

```json
{
  "knowledge_base_id": "kb-demo",
  "snapshot_id": "kb-demo-2026-02-16-001",
  "reference_version": "v1",
  "created_at": "2026-02-16T09:00:00",
  "source_docs": [
    {"id": "doc-1", "title": "Policy Manual v2", "date": "2025-06-10", "version": "2.0"}
  ],
  "entities": [
    {
      "id": "ent-001",
      "name": "Data Retention Policy",
      "domain": "policy",
      "facts": ["Retention is 24 months"],
      "reliability": 0.91,
      "provenance": ["doc-1"],
      "updated_at": "2025-06-10",
      "status": "active"
    }
  ],
  "relations": [
    {"source": "ent-001", "type": "implements", "target": "ent-002", "confidence": 0.84}
  ]
}
```

## Reference Policy

`data/reference.json` includes:

- `min_valid_date`
- `min_reliability`
- `required_domains`
- `prohibited_terms`
- `forbidden_statuses`
- `require_provenance`

## Validation Output

`ValidationReport` includes:

- `generated_at`
- `knowledge_base_id`
- `snapshot_id`
- `reference_version`
- `mode` (`deterministic` or `deterministic_and_ai`)
- `summary` (issue counters)
- `issues[]` (machine-readable findings)
- `clarification_questions[]`
- `ai_report` (optional text from Groq)

## Deterministic Checks Implemented

- Duplicate entity names
- Conflicting facts (e.g., 12 vs 24 months)
- Obsolete entities (`updated_at < min_valid_date`)
- Missing domain
- Low reliability
- Missing provenance
- Unknown provenance references
- Prohibited terms
- Forbidden statuses
- Missing required domains
- Relationship cycles (`depends_on` / `requires` / `parent_of`)

## Example Coverage Matrix

| Example file | Main scenario | Expected key issue codes |
|---|---|---|
| `01_valid_baseline.json` | Clean baseline | none or very low count |
| `02_duplicate_names.json` | Duplicate entity names | `DUPLICATE_ENTITY_NAME` |
| `03_conflicting_facts.json` | Contradictory retention facts | `CONFLICTING_FACTS`, `DUPLICATE_ENTITY_NAME` |
| `04_obsolete_data.json` | Stale data | `OBSOLETE_ENTITY` |
| `05_missing_domain.json` | Missing domain | `MISSING_DOMAIN`, `MISSING_REQUIRED_DOMAIN` |
| `06_low_reliability.json` | Reliability below threshold | `LOW_RELIABILITY` |
| `07_missing_provenance.json` | Empty provenance | `MISSING_PROVENANCE` |
| `08_prohibited_terms.json` | Prohibited language | `PROHIBITED_TERM` |
| `09_relationship_cycle.json` | Cyclic dependency | `RELATIONSHIP_CYCLE` |
| `10_missing_required_domain.json` | Required domain absent globally | `MISSING_REQUIRED_DOMAIN` |
| `11_unknown_provenance_source.json` | Provenance points to unknown document | `UNKNOWN_PROVENANCE_SOURCE` |
| `12_forbidden_status.json` | Forbidden status value | `FORBIDDEN_STATUS` |
| `13_multi_issue_mix.json` | Multi-failure stress case | multiple high-severity codes |

## API Endpoints

- `GET /api/v1/health`
- `GET /api/v1/knowledge`
- `PUT /api/v1/knowledge`
- `GET /api/v1/reference`
- `PUT /api/v1/reference`
- `POST /api/v1/validate`
- `POST /api/v1/validate-text`
- `GET /api/v1/validation-report`
- `GET /api/v1/examples`
- `POST /api/v1/load-example?name=...`
- `GET /api/v1/history`

## Quick Start (Local)

```bash
poetry install
PYTHONPATH=src poetry run python -m main
```

Service runs on `http://localhost:3000`.

## Optional AI Configuration (Groq)

If `GROQ_API_KEY` is configured, the service adds AI summary text to `ai_report`.
If not configured, deterministic validation still works.

```bash
export GROQ_API_KEY=your_key_here
```

## Sample Workflow

1. List examples:

```bash
curl -4 http://localhost:3000/api/v1/examples
```

2. Load one case:

```bash
curl -4 -X POST "http://localhost:3000/api/v1/load-example?name=13_multi_issue_mix.json"
```

3. Run validation:

```bash
curl -4 -X POST http://localhost:3000/api/v1/validate
```

4. Read latest report:

```bash
curl -4 http://localhost:3000/api/v1/validation-report
```

## Docker

```bash
docker compose up --build
```

## Tests

```bash
poetry run pytest
```
