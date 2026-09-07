# React-folio consolidation evidence

Project #24 requested a one-way consolidation from `googa27/cristobal-react-folio` into canonical `googa27/main_website` without deleting, archiving, or mutating the source repository.

## Scope implemented

- Source repository retained: `/tmp/googa27-portfolio-governance/cristobal-react-folio`.
- Canonical public site target: `/tmp/googa27-portfolio-governance/main_website`.
- Structured resume source: `cristobal-react-folio/src/data/resume.json`.
- Phone-redacted checked-in target with intentionally public email: `main_website/apps/web/src/data/react-folio-resume.json`.
- Static rendering adapter: `apps/web/src/lib/content.ts`.
- Public pages migrated to local content first: home, about, projects, and contact.
- The About page renders all migrated work entries and all migrated skill entries from the phone-redacted React-folio copy; home only uses a preview slice that links to the full About route.
- Backend dependency removed from public page rendering; FastAPI remains optional only for demonstrably dynamic features with separate source/freshness/security evidence.

## Original migration snapshot (historical)

| Artifact                                                 | Bytes | SHA256                                                             | Decision                                                                     |
| -------------------------------------------------------- | ----: | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| `cristobal-react-folio/src/data/resume.json`             | 13184 | `087110b34d66d12bacf36dfcfb8c979a17f4b0187e5cea9840bfa5f9ac61d4f5` | Canonical structured resume source.                                          |
| `cristobal-react-folio/public/data/resume.json`          |  6671 | `afcff3a6f25b10f5ad1eb8822b72a174d3938a2325d59a738d04770d43af13cc` | Not used as canonical because it is a truncated runtime/public copy.         |
| `main_website/apps/web/src/data/react-folio-resume.json` | 12985 | `9b0746a639cde0f822a20bf4c60b18148dfd542114c4961550876836fb950f5c` | Phone-redacted copy consumed by the static site; email remains public.       |
| `cristobal-react-folio/src/lib/resume/normalize.ts`      | 11047 | `98898dc249d1db7eb38a64419695da4ff29cbe29f74e2a6d2a814c9e79cb83d2` | Evidence for synthesized GitHub/LinkedIn defaults and hidden-phone behavior. |
| `cristobal-react-folio/MIGRATION.md`                     |  5047 | `34d8e79f2223613b1bc15d5d61a797fd1639fc5b81569829d436b37c5102d192` | Evidence for React-folio migration/privacy intent.                           |

At the original migration, the main-site resume copy preserved: 14 work entries, 4 education entries, 100 skills, 3 languages, 2 awards, 1 volunteer entry, and 2 certificates.

## Privacy and freshness controls

- `basics.phone` is intentionally excluded from the checked-in main-site copy and from all public rendering.
- Email is rendered only as a direct `mailto:` contact path; the static site does not collect or store contact form bodies.
- Profile links are mapped from the curated `basics.profiles` collection: LinkedIn, GitHub, Hugging Face and Kaggle.
- Project cards include `lastVerified` and evidence strings instead of runtime counters or unvalidated third-party cache claims.
- Dynamic adapters must record source, lineage, freshness/vintage, credential handling, and replay behavior before use.

## Static-first architectural decision

The canonical site now renders from local typed content:

1. React-folio source evidence ->
2. phone-redacted checked-in JSON with intentionally public email ->
3. `apps/web/src/lib/content.ts` typed public adapter ->
4. static Next.js pages.

`apps/web/next.config.ts` uses static export mode. `apps/web/src/lib/api.ts` remains only a compatibility shim over local curated projects plus a fail-closed contact method; public pages do not require the FastAPI backend.

## Original migration scope exclusions

- No repository visibility change.
- No source repository deletion/archive toggle.
- No commit, push, Dependabot merge, or GitHub mutation.
- No migration of generic placeholder assets or unused hero image; the consolidation is content/evidence-first to avoid copying unused assets into the canonical site.

## Profile evidence refresh — 6 September 2026

The curated copy was reconciled with the owner's corrections, LinkedIn timeline and public repositories. It retains 14 roles, two verified education entries, one award, one active certificate and seven grouped skill areas. Duplicate or unsupported credential entries and unrelated hard-coded skill claims were removed. Phone redaction and the intentionally public email remain in place. The source React-folio repository was not changed.

Finite Element Options now leads the project selection, with the synthetic online-only benchmark and experimental boundaries stated explicitly. Public visitor copy describes the work and career focus; internal migration details remain in this document.

The current curated artifact supersedes the historical main-site identity above. Its inventory is 14 work entries, 2 education entries, 7 skill groups, 3 languages, 1 award, 0 volunteer entries, 1 certificate, 3 source projects and 4 social profiles. The PUC score remains in the private master CV but is deliberately omitted from the public site. Current-role descriptions foreground development; the empty volunteer card is hidden.

The optional résumé chat service reads the typed public API fixture at startup for both model context and offline fallback. Project and award sections survive typed API JSON export. Restart that service after changing its checked-in profile. Public static pages remain independent of this optional service.

Current public artifact identity: `apps/web/src/data/react-folio-resume.json` — 11059 bytes; SHA-256 `d4b193e1150fdd5d1cea7494302e4c25218aac85d069892880b21757493d7c99`.
