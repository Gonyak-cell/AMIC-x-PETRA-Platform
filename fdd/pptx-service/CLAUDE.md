# PPTX Service — Node.js Sidecar Rules

## Stack
Express, PptxGenJS, TypeScript (strict), CommonJS module system

## Purpose
Receives Report Schema IR (JSON) from Python backend, renders PPT file, returns binary.
Called by backend via HTTP — NOT directly by frontend.

## Current State
- `GET /health` — working
- `POST /render` — returns 501 (stub)
- **DO NOT implement /render until Sprint 7** — Report Schema IR is not yet defined

## API Contract (Sprint 7+)
- POST /render: body = Report Schema IR JSON
- Response: PPT binary (`application/vnd.openxmlformats-officedocument.presentationml.presentation`)

## Testing
- `npm run build` — TypeScript compilation check (CI)
- `npm test` — Jest (no tests yet, Sprint 7+)
