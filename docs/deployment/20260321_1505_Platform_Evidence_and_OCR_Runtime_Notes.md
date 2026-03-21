**Scope**
This note covers the new platform-wide evidence API/runtime and the PDF OCR readiness checks added on March 21, 2026.

**Common Evidence**
- Common evidence rows are stored in `evidence_records`.
- Normalized parser chunks are stored in `document_chunks`.
- `LDD_REPORT` continues dual-write for safety.
- `FINANCIAL_MODEL` now writes common evidence rows from checklist-seeded sources.
- Query endpoint:
  - `GET /api/v1/transactions/{txn_id}/evidence/{artifact_type}/{artifact_id}`
  - optional query params: `workstream`, `section_type`, `item_id`, `analysis_phase`

**Artifact Types**
- `LDD_REPORT`
- `FINANCIAL_MODEL`

**External Import Bridge**
- Common import endpoint:
  - `POST /api/v1/transactions/{txn_id}/evidence/import`
- Current intended first producer outside this repo:
  - external `FDD_REPORT`
- Transaction-level pull endpoint for linked FDD deals:
  - `POST /api/v1/transactions/{txn_id}/integrations/fdd/evidence-sync`
- If `artifact_id` is omitted, the API derives a stable UUID from:
  - `txn_id + artifact_type + external_artifact_ref`

**FDD Operator Flow**
- Link the transaction to an FDD deal first:
  - `POST /api/v1/transactions/{txn_id}/integrations/fdd/link`
- Then pull the normalized FDD evidence export into common `evidence_records`:
  - `POST /api/v1/transactions/{txn_id}/integrations/fdd/evidence-sync`
- External FDD only needs to expose one normalized export payload at:
  - `GET {FDD_API_URL}/deals/{deal_id}/evidence-export`
- Validation helper:
  - `python scripts/validate_fdd_evidence_export.py --deal-id <uuid>`

**OCR Runtime Flags**
- `OCR_ENABLED=true|false`
- `OCR_ENGINE=tesseract`
- `OCR_LANGUAGES=kor+eng`
- `OCR_REQUIRE_FOR_SCANNED_PDF=true|false`
- `TESSERACT_CMD=<absolute path>` if the binary is not on `PATH`

**Health Check**
- `/health` now includes an `ocr` object.
- If `OCR_REQUIRE_FOR_SCANNED_PDF=true` and OCR is unavailable, health becomes `degraded`.
- If OCR is optional and unavailable, health stays `ok` but the startup log warns.

**Operational Note**
- The code can now fall back to OCR for scanned PDFs, but actual recovery quality still depends on `pytesseract` and a working Tesseract binary being installed on the runtime host.
- If `pytesseract` is missing, scanned PDFs fall back to native parsing only unless `OCR_REQUIRE_FOR_SCANNED_PDF=true`, in which case the parser surfaces an explicit error.
- Windows helper:
  - `.\scripts\install-tesseract-windows.ps1`
- Health helper:
  - `.\scripts\health-check.ps1` now prints the MA API OCR runtime block
- On this machine, `TESSERACT_CMD` can be pinned to:
  - `C:\Program Files\Tesseract-OCR\tesseract.exe`
