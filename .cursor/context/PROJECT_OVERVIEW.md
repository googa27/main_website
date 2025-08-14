# PROJECT OVERVIEW

**Primary objective (current):** land interviews and impress recruiters with a professional, fast portfolio.  
**Secondary (phased later):** interactive AI/quant demos, blog, and light monetization.

## Non‑negotiables
- Ship a clean, credible MVP fast; avoid scope creep.
- Prefer scalability and clear architecture over hacks.
- Keep costs ~$0 at first; upgrade only when monetization justifies it.

## What to build (MVP)
- Public pages: Home, About, Projects, Contact.
- Projects page pulls data (static JSON for now or via FastAPI endpoint).
- Contact form posts to backend; send email or store message.
- Optional: auth only if it doesn’t slow delivery (see AUTH & MONETIZATION).

## Working rules for the AI
- Use **Next.js** for the frontend (TypeScript preferred, JavaScript acceptable).  
- Use **FastAPI (Python 3.11+)** for the backend; define schemas with **Pydantic**.  
- Style with **Tailwind CSS** by default; alternatives allowed if they simplify or improve DX.  
- Write **docstrings** and **type hints** everywhere. Enforce **Black** (Python) and **Prettier/ESLint** (web).  
- Follow SOLID in the backend and keep components small & testable on the frontend.
- Prefer **file‑based config** and **12‑factor** practices.

## Hosting & Infra (starter plan)
- **Frontend:** deploy to **Vercel** (Hobby) for Next.js (CI/CD + global CDN). If monetization is enabled, consider upgrading to **Pro** or alternative hosting due to free‑tier commercial use limits.  
- **Backend:** deploy **FastAPI** on **Render** free web service for MVP; attach a free Postgres if needed.  
- **Database:** start with **Neon Serverless Postgres** (scale‑to‑zero, generous free tier) or **Supabase** if you want managed auth/files in one place. (Pick ONE.)

## Data & content
- Start with a local `data/projects.json`. Expose `/api/projects` in FastAPI later.
- Store environment secrets only in the platform (Vercel/Render/Neon/Supabase). Never commit secrets.

## Roadmap (phases)
1) **MVP** (this sprint): pages + styling + contact form (wired to FastAPI) + projects JSON.  
2) **Hardening**: tests, a11y, perf checks, analytics.  
3) **Demos**: add 1 interactive AI/quant demo (server‑driven).  
4) **Monetization**: add a donation button or Sponsors; Stripe/paid content later.

