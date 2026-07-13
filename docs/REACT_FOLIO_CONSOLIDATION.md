# React-folio consolidation evidence

Project #24 requested a one-way consolidation from `googa27/cristobal-react-folio` into canonical `googa27/main_website` without deleting, archiving, or mutating the source repository.

## Scope implemented

- Source repository retained: `/tmp/googa27-portfolio-governance/cristobal-react-folio`.
- Canonical public site target: `/tmp/googa27-portfolio-governance/main_website`.
- Structured resume source: `cristobal-react-folio/src/data/resume.json`.
- Redacted checked-in target: `main_website/apps/web/src/data/react-folio-resume.json`.
- Static rendering adapter: `apps/web/src/lib/content.ts`.
- Public pages migrated to local content first: home, about, projects, and contact.
- The About page renders all migrated work entries and all migrated skill entries from the redacted React-folio copy; home only uses a preview slice that links to the full About route.
- Backend dependency removed from public page rendering; FastAPI remains optional only for demonstrably dynamic features with separate source/freshness/security evidence.

## Source identity and migration evidence

| Artifact                                                 | Bytes | SHA256                                                             | Decision                                                                     |
| -------------------------------------------------------- | ----: | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| `cristobal-react-folio/src/data/resume.json`             | 13184 | `087110b34d66d12bacf36dfcfb8c979a17f4b0187e5cea9840bfa5f9ac61d4f5` | Canonical structured resume source.                                          |
| `cristobal-react-folio/public/data/resume.json`          |  6671 | `afcff3a6f25b10f5ad1eb8822b72a174d3938a2325d59a738d04770d43af13cc` | Not used as canonical because it is a truncated runtime/public copy.         |
| `main_website/apps/web/src/data/react-folio-resume.json` | 12985 | `9b0746a639cde0f822a20bf4c60b18148dfd542114c4961550876836fb950f5c` | Redacted copy consumed by the static site.                                   |
| `cristobal-react-folio/src/lib/resume/normalize.ts`      | 11047 | `98898dc249d1db7eb38a64419695da4ff29cbe29f74e2a6d2a814c9e79cb83d2` | Evidence for synthesized GitHub/LinkedIn defaults and hidden-phone behavior. |
| `cristobal-react-folio/MIGRATION.md`                     |  5047 | `34d8e79f2223613b1bc15d5d61a797fd1639fc5b81569829d436b37c5102d192` | Evidence for React-folio migration/privacy intent.                           |

The main-site resume copy preserves the structured resume content needed by the public renderer: 14 work entries, 4 education entries, 100 skills, 3 languages, 2 awards, 1 volunteer entry, and 2 certificates.

## Privacy and freshness controls

- `basics.phone` is intentionally excluded from the checked-in main-site copy and from all public rendering.
- Email is rendered only as a direct `mailto:` contact path; the static site does not collect or store contact form bodies.
- GitHub and LinkedIn links are explicit static profile links, with provenance from React-folio normalization behavior.
- Project cards include `lastVerified` and evidence strings instead of runtime counters or unvalidated third-party cache claims.
- Dynamic adapters must record source, lineage, freshness/vintage, credential handling, and replay behavior before use.

## Static-first architectural decision

The canonical site now renders from local typed content:

1. React-folio source evidence ->
2. redacted checked-in JSON ->
3. `apps/web/src/lib/content.ts` typed public adapter ->
4. static Next.js pages.

`apps/web/next.config.ts` uses static export mode. `apps/web/src/lib/api.ts` remains only a compatibility shim over local curated projects plus a fail-closed contact method; public pages do not require the FastAPI backend.

## Out of scope / explicitly not done

- No repository visibility change.
- No source repository deletion/archive toggle.
- No commit, push, Dependabot merge, or GitHub mutation.
- No migration of generic placeholder assets or unused hero image; the consolidation is content/evidence-first to avoid copying unused assets into the canonical site.
