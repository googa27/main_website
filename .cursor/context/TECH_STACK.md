# TECH STACK & CHOICES

## Frontend
- **Framework:** Next.js (App Router).  
- **Language:** TypeScript (preferred).  
- **Styling:** Tailwind CSS; may add shadcn/ui for primitives.  
- **State & data:** fetch with RSC or `getStaticProps` as appropriate; keep client state minimal.

## Backend
- **Framework:** FastAPI (Python 3.11+).  
- **Models:** Pydantic; routers per domain.  
- **Mail:** `fastapi-mail` or provider SDK for contact form.  
- **CORS:** `CORSMiddleware` allow only site origin.

## Database
- **Option A (pure Postgres):** Neon (serverless, scale to zero).  
- **Option B (toolkit):** Supabase (Postgres + auth + storage) if reducing glue code is worth the coupling.

## Hosting
- **Frontend:** Vercel (Hobby -> Pro if commercial use).  
- **Backend:** Render free web service for FastAPI.  
- **DB:** Neon or Supabase managed Postgres.

## Tooling & Quality
- **Formatting:** Black (Python), Prettier (web).  
- **Linting:** Ruff (Python), ESLint (web).  
- **Tests:** pytest (API), React Testing Library or Playwright (web).  
- **CI:** GitHub Actions for lint/test on PR, auto‑deploy via Vercel/Render.

## Architecture Notes
- Decoupled FE/BE; communicate via HTTP/JSON.  
- Keep API surface small: `/api/projects`, `/api/contact`.  
- Use `.env` locally; secrets via platform envs in prod.

