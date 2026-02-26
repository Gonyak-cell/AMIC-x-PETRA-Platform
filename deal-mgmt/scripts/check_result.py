"""Pipeline 결과 JSON 확인 스크립트."""

import json

with open("output/pipeline_result.json", encoding="utf-8") as f:
    data = json.load(f)

# Executive summary
es = data.get("executive_summary", "")
print("=== EXECUTIVE SUMMARY ===")
print(es[:2000] if es else "(empty)")
print()

# Narrative count
ns = data.get("narrative_sections", {})
total = sum(len(items) for items in ns.values())
print(f"=== NARRATIVE: {len(ns)} sections, {total} blocks ===")
for sec, items in ns.items():
    print(f"  {sec}: {len(items)} blocks")

# Gap detection
gap = data.get("gap_detection", {})
print("\n=== GAP DETECTION ===")
if gap:
    for k, v in gap.items():
        if isinstance(v, list):
            print(f"  {k}: {len(v)} items")
        else:
            print(f"  {k}: {v}")

# Dual risk
dr = data.get("dual_risk_summary", {})
print("\n=== DUAL RISK ===")
print(f"  {json.dumps(dr, ensure_ascii=False)[:500]}")

# Cost
print(f"\n=== COST: ${data.get('cost_usd', 0):.4f} ===")

# Guardrails
gr = data.get("guardrail_result", {})
print("\n=== GUARDRAILS ===")
print(f"  errors: {gr.get('error_count', 0)}, warnings: {gr.get('warning_count', 0)}")
print(f"  passed: {gr.get('passed_rules', [])}")

# QA
qa = data.get("qa_result", {})
print("\n=== QA ===")
if qa:
    print(f"  overall_score: {qa.get('overall_score', 'N/A')}")
    print(f"  summary: {qa.get('summary', 'N/A')[:500]}")
    nq = qa.get("narrative_quality", {})
    if nq:
        print(f"  narrative: {nq.get('passed_items')}/{nq.get('total_items')} passed, score {nq.get('overall_score')}")
