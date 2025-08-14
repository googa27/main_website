# IMPLEMENTATION PLAN (Directive)

## Week 0 — Repo & Scaffolding
- Create monorepo (Turborepo optional) or two repos; initialize Next.js + FastAPI.  
- Add lint/format tooling and pre‑commit hooks.  
- Add Tailwind; create base layout, NavBar, and Footer.

## Week 1 — MVP Pages
- Home (hero, CTA), About (bio), Projects (cards from `data/projects.json`), Contact (form).  
- Reusable components: `ProjectCard`, `Section`, `Button`.  
- Responsive design and a11y checks.

## Week 2 — Backend & Wiring
- FastAPI: `/api/projects` (reads JSON), `/api/contact` (send email).  
- Add CORS.  
- Connect FE to BE; handle loading/error states; user‑visible success message.

## Week 3 — Hardening & Deploy
- Tests (pytest; minimal FE tests).  
- Lighthouse pass; basic analytics.  
- Deploy: Vercel (FE), Render (BE), Neon/Supabase (DB if needed).  
- Add `README` with run/deploy instructions.

## Stretch — First Demo
- Minimal AI/quant demo page calling FastAPI (no heavy models on FE).  
- Stream or simple POST/response.

