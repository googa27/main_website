# Reusable Prompts & Tasks

> Tip (Windsurf/Copilot/Continue): mention context explicitly when useful:
> “Use `docs/ai/CONTEXT.md` and `apps/api/app/models/project.py`.”

## Scaffolding & Glue
- **Create a ProjectCard and list page**
  “Read `docs/ai/CONTEXT.md`. In `apps/web/src/components/ProjectCard.tsx`, create a card component with props { title, summary, tags, repoUrl }. In `apps/web/src/app/projects/page.tsx`, map over data and render the cards. Use Tailwind utilities from our style. Keep it server-rendered.”

- **Hook Next.js to FastAPI**
  “Open `apps/web/src/app/projects/page.tsx`. Replace the local data with a server-side fetch to `http://127.0.0.1:8000/projects`. Add basic error states and a `revalidate = 60` export.”

- **Contact form POST**
  “In `apps/web/src/app/contact/page.tsx`, implement a form that POSTs JSON to `http://127.0.0.1:8000/contact`. On success, show a thank-you; on error, show a retry CTA. Don’t block UI; use `useFormStatus` or a minimal loading state.”

## Refactoring & Quality
- **Enforce conventions**
  “Review `apps/api/app/routers/*.py` for consistency with `docs/ai/CONTEXT.md` guidelines (naming, error handling). Propose a diff only.”

- **Add first tests**
  “Create `apps/api/tests/test_health.py` using FastAPI TestClient to assert `/health` returns 200 + `{'ok': True}`. Then add a Playwright test that loads `/contact`, fills the form, and verifies the success message (stub network with a 200).”

## Docs & Contracts
- **Export OpenAPI**
  “Write a small script (Python or npm) to GET `http://127.0.0.1:8000/openapi.json` and save it to `docs/api/openapi.json`. Add a README snippet showing how to regenerate. Then wire `openapi-typescript` in the web app to generate client types.”

## Fixers (copy when something goes wrong)
- **CORS**
  “I’m getting a CORS error calling FastAPI from Next.js dev. Inspect `apps/api/app/main.py` and fix `allow_origins` to include `http://localhost:3000` and `http://127.0.0.1:3000`. Show just the changed lines.”

- **Type drifts**
  “TS types don’t match API schema. Use `docs/api/openapi.json` to regenerate types and apply minimal diffs to fetchers/components. Do not change runtime logic.”

## Code Review Prompt
“Act as a strict reviewer. Using `docs/ai/CONTEXT.md` as the source of truth, review changes under `apps/api/app/routers` and `apps/web/src/app/projects`. Flag style violations, missing tests, and unclear error handling. Propose concise diffs.”
