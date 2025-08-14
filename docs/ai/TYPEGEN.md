# API Types Pipeline (FastAPI → OpenAPI → TypeScript)

## TL;DR
- Export schema: `python apps/api/scripts/export_openapi.py` → `docs/api/openapi.json`
- Generate types: `cd apps/web && pnpm dlx openapi-typescript ../../docs/api/openapi.json -o src/types/openapi.ts`
- Use client: import `createClient` from `openapi-fetch` and `paths` from `@/types/openapi`.

## Why this setup
- FastAPI exposes OpenAPI at `/openapi.json` and via `app.openapi()` (no server needed).
- `openapi-typescript` generates types; `openapi-fetch` gives a tiny, zero-magic client with full inference.

## Commands
```bash
# export (repo root)
python apps/api/scripts/export_openapi.py

# generate (apps/web)
pnpm dlx openapi-typescript ../../docs/api/openapi.json -o src/types/openapi.ts
```
