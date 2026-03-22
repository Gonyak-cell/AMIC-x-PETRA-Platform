# LDD Phased Rollout Plan

## Goal

Ship the LDD improvements in three controlled bundles so we can isolate failures quickly and roll back without losing the whole release.

## Bundle A: Template Compiler

### Scope

- `deal-mgmt/app/ralph/generators/ldd/project_green_style.py`
- `deal-mgmt/app/ralph/generators/ldd/slot_fill/`
- `deal-mgmt/templates/ldd_slotfill/`
- `deal-mgmt/app/services/ldd_report_service.py`
- `deal-mgmt/tests/test_ldd_slot_fill.py`
- `deal-mgmt/tests/test_ldd_docx_regression.py`

### Release Lever

- Primary flag: `LDD_TEMPLATE_SLOTFILL_ENABLED`
- Safety setting: `LDD_TEMPLATE_SLOTFILL_USE_LLM=False`

### Why First

- This bundle improves output consistency while staying deterministic.
- It already has direct DOCX regression coverage for `FULL`, `REDFLAG`, and `LAW_FIRM`.

### Success Criteria

- Slot-fill regression suite passes
- DOCX regression suite passes
- Manual review confirms section preambles and recommendation text are stable

### Stop Conditions

- Placeholder remnants in rendered DOCX
- Missing recommendation text
- Section preamble duplication regression

## Bundle B: Source Controls And Evidence Ledger

### Scope

- `deal-mgmt/app/services/workstream_router_service.py`
- `deal-mgmt/app/services/ldd_source_controls.py`
- `deal-mgmt/app/models/ldd_evidence_record.py`
- `deal-mgmt/app/models/ldd_report.py`
- `deal-mgmt/migrations/versions/085_ldd_source_control_columns.py`
- `deal-mgmt/migrations/versions/086_ldd_evidence_records_and_chunks.py`
- `deal-mgmt/tests/test_ldd_source_controls.py`
- `deal-mgmt/tests/test_financial_model_source_routing.py`

### Release Lever

- Primary thresholds:
  - `LDD_ROUTER_MIN_COMMON_CONFIDENCE`
  - `LDD_QA_CRITICAL_BLOCKS_READY`
- Operational fallback:
  - keep the backend deployed but lower traffic to VDR-backed generation if unexpected source-control blocks appear

### Why Second

- This bundle changes persisted data, routing, and QA behavior.
- It is the most important quality-control layer, but it also has the biggest operational blast radius.

### Success Criteria

- Routing summary is stored on VDR-backed reports
- Evidence ledger is stored and evidence records are persisted
- Foreign-workstream contamination and unresolved refs are blocked before `READY`

### Stop Conditions

- Unexpected spike in blocked reports caused by routing noise
- Legitimate LDD documents repeatedly routed out of the LDD path
- Evidence ledger rows missing after successful analysis

## Bundle C: VDR Routing Triage UX

### Scope

- `amic-platform/src/modules/ma/components/vdr/VdrRoutingTriagePanel.tsx`
- `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx`
- `amic-platform/src/modules/ma/hooks/useVdr.ts`
- `deal-mgmt/app/services/vdr_routing_service.py`
- `deal-mgmt/app/models/vdr_document_routing_override.py`
- `deal-mgmt/migrations/versions/087_vdr_routing_triage_queue.py`

### Release Lever

- This bundle does not yet have a dedicated global feature flag.
- Roll it out only after Bundle B is stable, because the UI depends on the routing model being trustworthy.

### Why Third

- It is operational tooling, not the core LDD compiler.
- Shipping it last keeps the user-visible change surface smaller during the main LDD release.

### Success Criteria

- Routing queue loads in production
- Manual overrides persist and are reflected in subsequent routing results
- No regression in the existing VDR document tabs

### Stop Conditions

- Override writes fail
- Queue loads but shows stale effective routes
- Frontend tab regressions affect normal VDR browsing

## Release Sequence

1. Deploy Bundle A and hold for a shadow-mode window.
2. Deploy Bundle B after Bundle A output is accepted by legal reviewers.
3. Deploy Bundle C only after Bundle B routing statistics look stable.

## Commit Split Recommendation

1. `feat(ldd): stabilize slot-fill compiler and docx regressions`
2. `feat(ldd): add workstream router, evidence ledger, and source-control QA`
3. `feat(vdr): add routing triage queue and manual override workflow`
4. `docs(release): add stability checklist and staged rollout plan`

## Current Limits

- The router already emits `LDD / FDD / VALUATION / COMMON` tags.
- The hardened end-to-end consumption path is implemented for LDD first.
- FDD and valuation can reuse the router, but they should not be marketed as fully migrated to the same quality-control flow until their own consumers and regressions are wired.
