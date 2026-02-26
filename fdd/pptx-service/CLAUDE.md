# PPTX Service — Node.js Sidecar Rules

## Stack
Express, PptxGenJS, TypeScript (strict), CommonJS module system

## Purpose
Receives Report Schema IR (JSON) from Python backend, renders PPT file, returns binary.
Called by backend via HTTP — NOT directly by frontend.

## Current State
- `GET /health` — working (returns version 0.2.0)
- `POST /render` — **fully implemented** (10 block type renderers)
- `POST /preview` — working (returns section summary JSON)

## Implemented Block Renderers
| BlockType | Function | Line |
|-----------|----------|------|
| cover | `renderCoverSlide()` | L267 |
| kpi | `renderKPISlide()` | L346 |
| table | `renderTableSlide()` | L417 (overflow pagination) |
| chart | `renderChartSlide()` | L550 (bar/line/pie + image_base64) |
| text | `renderTextSlide()` | L680 (risk_level badge) |
| claim | `renderClaimSlide()` | L767 (verified badge + evidence) |
| issue | `renderIssueSlide()` | L869 (severity color coding) |
| methodology | `renderMethodologySlide()` | L946 |
| scope | `renderScopeSlide()` | L1044 |
| appendix | `renderAppendixSlide()` | L1112 |

## API Contract
- `POST /render`: body = Report Schema IR JSON (`{ meta, sections, design_system? }`)
- Response: PPT binary (`application/vnd.openxmlformats-officedocument.presentationml.presentation`)
- Input limit: 50MB JSON body
- Design system: customizable colors, fonts, sizes (merges with defaults)

## Design System Defaults
- Colors: primary=#003366, secondary=#0066CC, positive=#2E7D32, negative=#E0301E
- Fonts: heading/body=맑은 고딕, data=Calibri
- Sizes: slide_title=28, section_title=24, body=14, table_header=11, table_body=10

## Testing
- `npm run build` — TypeScript compilation check (CI)
- `npm test` — Jest
