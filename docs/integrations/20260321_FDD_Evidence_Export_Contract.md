**Scope**
This contract defines the normalized FDD evidence export that the MA platform expects from the external FDD service.

**Endpoint**
- `GET {FDD_API_URL}/deals/{deal_id}/evidence-export`

**Payload shape**
- Top level fields:
  - `artifact_type`: usually `FDD_REPORT`
  - `artifact_id`: optional UUID
  - `external_artifact_ref`: optional stable external reference
  - `default_workstream`: usually `FDD`
  - `records`: array of normalized evidence rows
- Each `records[]` item should match [evidence.py](C:/Users/서지원/App/02_Platform/deal-mgmt/app/schemas/evidence.py)

**Minimum practical row**
```json
{
  "artifact_type": "FDD_REPORT",
  "external_artifact_ref": "fdd-<deal-id>",
  "default_workstream": "FDD",
  "records": [
    {
      "section_type": "WORKING_CAPITAL",
      "item_id": "NWC-01",
      "reference_label": "qoe_report.xlsx",
      "original_name": "qoe_report.xlsx",
      "primary_workstream": "FDD",
      "workstream_tags": ["FDD"],
      "evidence_kind": "FINANCIAL_SUPPORT",
      "directness": "INDIRECT",
      "confidence": 0.86,
      "relevance_score": 0.86,
      "source_page": "Sheet QoE Row 4",
      "source_snippet": "Working capital support.",
      "used_in_draft": false,
      "used_in_final": true,
      "analysis_phase": "FINAL"
    }
  ]
}
```

**How to validate before cutover**
- Fetch from the external service:
  - `python scripts/validate_fdd_evidence_export.py --deal-id <uuid>`
- Validate a saved payload file:
  - `python scripts/validate_fdd_evidence_export.py --input-json path/to/export.json`

**How the MA platform consumes it**
- Pull and import for a linked transaction:
  - `POST /api/v1/transactions/{txn_id}/integrations/fdd/evidence-sync`
- Direct import bridge:
  - `POST /api/v1/transactions/{txn_id}/evidence/import`

**Cutover checklist**
- The FDD service returns `200` with a schema-valid payload for a real `deal_id`.
- `record_count > 0` for at least one live test deal.
- The MA platform `evidence-sync` call imports rows without validation errors.
- `GET /api/v1/transactions/{txn_id}/evidence/FDD_REPORT/{artifact_id}` returns the imported rows.
