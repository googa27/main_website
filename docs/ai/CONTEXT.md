# Project Context (AI-Readable)

## Mission
Build a maintainable, extensible personal site with **Next.js (TypeScript)** for the UI and **FastAPI (Python)** for APIs.
Initial scope: **Home, About, Projects, Contact**. Future: blog, AI demos, auth/monetization.

## Tech Stack
- **Frontend:** Next.js App Router, Tailwind CSS (optionally shadcn/ui).
- **Backend:** FastAPI + Pydantic; email via SMTP (dev logs if not configured).
- **Deployment:** Vercel (web), Render/Fly (API).
- **Quality:** ESLint/Prettier (web), Ruff/Black/Pytest (api).

## Repository Layout
apps/
  web/ # Next.js (src/app, components, lib, styles, public)
  api/ # FastAPI (app/{routers,services,models,core}, data/)
docs/
  ai/ # AI context & prompts
  adr/ # (optional) architecture decisions


## Data Flow (MVP)
Browser → Next.js (SSR/SSG) → (if needed) FastAPI
- `/projects`: list comes from `apps/api/app/data/projects.json` (later: DB).
- `/contact`: POST {name,email,message} → FastAPI → SMTP or dev log.

## Coding Guidelines (short)
- **TS/React:** server components by default, client components only for interactivity.
- **Naming:** `camelCase` for vars, `PascalCase` for components, `snake_case` in Python.
- **Errors:** narrow try/catch; surface user-friendly messages.
- **Tests:** API: pytest for routers/services. Web: Playwright e2e for critical paths.

## Non-Goals (MVP)
- No user auth, DB, or payments (placeholders only). No heavy ML libs in API.

## TODO / Near-Term
- [ ] Projects page renders from API (swap local JSON → HTTP fetch).
- [ ] Contact form wired to `POST /contact` with optimistic UI + error states.
- [ ] Add `openapi.json` under `docs/api/` (scripted export from FastAPI).
- [ ] 1 e2e test (submit contact) + 1 API test (`/health`).

## Prompts (quick links)
See `docs/ai/PROMPTS.md` for copy-paste tasks and “fix” prompts.
