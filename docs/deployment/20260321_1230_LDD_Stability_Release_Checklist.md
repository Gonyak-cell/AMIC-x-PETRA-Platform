# LDD Stability Release Checklist

## Scope

- Release candidate workspace: `C:\Users\서지원\App\02_Platform_ported_0_15_1`
- Release branch: `rebuild/ported-0.15.1`
- Production baseline: `0.15.1`
- Objective: ship the LDD slot-fill, evidence-ledger, and VDR routing changes with the lowest possible operational risk

## Freeze Decisions

- Freeze the runtime bank in `deal-mgmt/templates/ldd_slotfill/` before release day.
- Keep `LDD_TEMPLATE_SLOTFILL_USE_LLM=False` during the first rollout window.
- Treat `ldd/ldd_slotfill_bank_from_samples_v8/` as the source-of-truth extraction artifact set for this release.
- Do not change the slot-fill bank and renderer logic in the same deployment window unless a blocking bug is found.
- Apply migrations `085`, `086`, `087` together as one backend schema set.

## Pre-Deploy Checks

- Confirm `VERSION` is still aligned with the intended release label.
- Confirm `alembic heads` returns only `087 (head)`.
- Confirm the focused LDD regression bundle passes:
  - `python -m pytest -o addopts='' tests/test_ldd_slot_fill.py tests/test_ldd_templates.py tests/test_ldd_law_firm.py tests/test_ldd_docx_regression.py tests/test_ldd_reports.py -q`
- Confirm the source-control regression bundle passes:
  - `python -m pytest -o addopts='' tests/test_ldd_source_controls.py tests/test_vdr.py tests/test_financial_model_source_routing.py -q`
- Confirm the frontend routing tab regression passes:
  - `npm test -- --run src/modules/ma/components/vdr/__tests__/VdrTab.test.tsx`
- Confirm the frontend production build succeeds:
  - `npm run build`

## Manual Sign-Off

- Generate one `FULL` LDD report and verify:
  - no unreplaced placeholders
  - section preambles appear once per section
  - recommendation text appears in the final DOCX
- Generate one `REDFLAG` LDD report and verify:
  - only issue items appear
  - OK items do not leak into the rendered report
- Generate one `LAW_FIRM` LDD report and verify:
  - cover, TOC, chapter mapping, and recommendation text render correctly
  - the tone selector uses `판단됩니다 / 보입니다 / 사료됩니다` appropriately
- Review one VDR-backed report and verify:
  - `source_routing` is persisted
  - `evidence_ledger` is persisted
  - unresolved evidence, foreign workstream evidence, and placeholder remnants hard-block readiness

## Data Safety

- Back up the production database immediately before applying migrations `085`, `086`, `087`.
- Snapshot the `ldd_reports` and new `ldd_evidence_records` tables after migration and before traffic cutover.
- Preserve the runtime bank YAML files and `ldd/ldd_slotfill_bank_from_samples_v8/` artifacts together in the release branch.

## Release Flags

- `LDD_TEMPLATE_SLOTFILL_ENABLED=True`
- `LDD_TEMPLATE_SLOTFILL_USE_LLM=False`
- `LDD_ROUTER_MIN_COMMON_CONFIDENCE=0.55`
- `LDD_QA_CRITICAL_BLOCKS_READY=True`

## Shadow Mode

- For the first rollout window, run the new LDD generation path for a controlled set of transactions only.
- Keep the previous production branch/tag ready for rollback.
- Compare old vs new output for at least:
  - one governance-heavy case
  - one contracts-heavy case
  - one permits-heavy case
- Track these counts during shadow mode:
  - placeholder failures
  - unresolved evidence references
  - foreign workstream contamination
  - manual routing override count
  - docx generation failures

## Go Criteria

- No migration errors
- No placeholder remnants in release-sample DOCX outputs
- No unexpected READY reports with hard-block QA issues
- No rise in docx generation failures during shadow mode
- Manual legal review signs off on the selected release samples

## Rollback Criteria

- Migration failure or unexpected schema drift
- READY reports generated with unresolved placeholders
- LDD reports contaminated by FDD or valuation-only documents
- Recommendation text missing from `LAW_FIRM` output
- More than one reproducible docx generation failure on release samples

## Rollback Steps

- Revert traffic to the previous production tag/branch.
- Set `LDD_TEMPLATE_SLOTFILL_ENABLED=False` if rollback needs to keep the same backend build alive.
- Keep `LDD_QA_CRITICAL_BLOCKS_READY=True` unless the incident is proven to be a false-positive gate bug.
- Restore the database snapshot only if the schema or persisted evidence records are corrupted.

## Post-Deploy Follow-Up

- Review the first 10 VDR-backed LDD reports generated after release.
- Inspect routing overrides and triage queue activity daily during the first week.
- Delay any further bank promotion until at least one stable shadow-mode cycle completes.
