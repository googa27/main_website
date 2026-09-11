# Architecture — main_website

<!-- PORTFOLIO-CONSTITUTION:START -->

## Portfolio architecture baseline

Source of truth: `docs/ARCHITECTURE.yaml`. Tracking: [Project #24](https://github.com/users/googa27/projects/24), [main_website issue](https://github.com/googa27/main_website/issues/84). Profile: `application`; enforcement: `Blocking`.

### Research-backed defaults

| Decision             | Evidence                                                                                                                                              | Repository application                                                                                 |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Agent context        | [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files), [AGENTS.md](https://agents.md/)                 | Root `AGENTS.md`; progressive detail stays in linked docs.                                             |
| AI tool escalation   | [MCP tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)                                                      | Stable CLI/contracts and skills first; plugin/MCP only after measured need and least-privilege review. |
| Python source layout | [PyPA src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)                                                      | Declared Python roots: `none yet`.                                                                     |
| Test layout          | [pytest good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)                                                             | Unit/integration/e2e/architecture boundaries are explicit.                                             |
| Module budget        | [Pylint too-many-lines rationale](https://pylint.readthedocs.io/en/latest/user_guide/messages/convention/too-many-lines.html) plus AI review locality | 500 physical lines is stricter than Pylint's broad default; existing excess is a no-growth ratchet.    |
| Evolution            | [Evolutionary architecture](https://evolutionaryarchitecture.com/precis.html)                                                                         | Architecture characteristics have executable fitness functions and incremental exceptions.             |
| Data layers          | [Medallion architecture](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)                                                      | Applied only where data is consumed; simple repos record an explicit non-use decision.                 |
| Python protocols     | [Python data model](https://docs.python.org/3/reference/datamodel.html), [NumPy dispatch](https://numpy.org/doc/stable/user/basics.dispatch.html)     | Dunders express true protocols/laws; named methods own policy and effects.                             |

### Maintained-library decision table

| Capability                      | Selected route                                                                               | Alternatives                                         | Boundary / custom-code rule                                                                  |
| ------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Existing runtime stack          | `@repo/config`, `husky`, `lint-staged`, `prettier`, `turbo`                                  | Reimplementation from scratch                        | Preserve public adapters; research maintenance/API/license before additions.                 |
| Architecture contract bootstrap | Python standard-library JSON parser over the JSON subset of YAML 1.2                         | Hand-written YAML parser; mandatory platform service | Repo-local dependency-free structural gate; richer maintained tools remain repo-specific.    |
| Import/dependency rules         | Existing repo lint/import tools where configured; declarative YAML boundary is authoritative | Custom import framework                              | Keep custom AST checks narrow; use maintained Import Linter/Tach/Ruff/deptry when warranted. |
| AI interaction                  | AGENTS + deterministic CLI/contracts + capability discovery + skills                         | MCP/plugin in every repo                             | Escalate only after measured interoperability/lifecycle need.                                |

### Two-user design

- AI: AGENTS + deterministic frontend/backend commands and capability notes; no MCP/plugin by default.
- Human/notebook: Typed app/service APIs; notebook use only for isolated analytics services; no clever dunders.
- Planned Python protocols: Python dunders apply only to FastAPI support code; the static web path uses language-native TypeScript contracts.
- Core posture: Consume prebuilt ui_and_artifacts outputs; no PDP/FPF internals.
- Data posture: Static-first public content adapter with curated/redacted React-folio resume JSON; optional API adapters remain separate from presentation and must record source/freshness/evidence before use.
- Consolidation evidence: `docs/REACT_FOLIO_CONSOLIDATION.md` records the one-way React-folio to main_website migration, phone redaction, static export posture, and explicit source-repository retention.
- CV storage: `CVService` resolves its default `app/static/cv` directory relative to the application module. Importing and exporting from another working directory uses the same public profile and creates no `app/` directory in the caller's location; an API regression protects this behavior (issue #105).

### Executive summary: optional API time and HTTP clients

- **UTC timestamps:** `apps/api/app/core/time.py::utc_now` is the single clock factory for generated API timestamps. It returns aware UTC values; ORM timestamp columns declare `DateTime(timezone=True)`.
- **Legacy data:** the repository has Alembic scaffolding but no revision baseline. `UTCDateTime` therefore interprets existing naive timestamps as UTC and restores aware UTC values after database reads rather than claiming an unexecuted production migration. PostgreSQL preserves timezone semantics directly; SQLite may discard offsets internally, but the application boundary restores them before consumers or serializers observe the value.
- **HTTP ownership:** `httpx` remains the runtime client used by the GitHub adapter. `httpx2` is development-only and backs Starlette/FastAPI `TestClient`, as recommended by current Starlette documentation. HTTPX2 2.12.0 is the Pydantic-maintained BSD-3-Clause distribution ([source and release](https://github.com/pydantic/httpx2/releases/tag/v2.12.0), [package metadata](https://pypi.org/project/httpx2/2.12.0/)); it selects exact HTTPcore2 2.12.0. Starlette 1.6.0 [explicitly selects HTTPX2](https://github.com/Kludex/starlette/blob/1.6.0/starlette/testclient.py#L29-L48) and warns on the canonical HTTPX fallback. This development-only upgrade resolves the stale test-transport audit findings tracked in [#106](https://github.com/googa27/main_website/issues/106); runtime HTTP ownership is unchanged.
- **Fail-closed verification:** API tests promote Python and Starlette deprecations to errors. `apps/api/tests/test_datetime_contracts.py` forbids `datetime.utcnow`, verifies timezone-aware ORM declarations and CV defaults, and proves TestClient selected HTTPX2 rather than its deprecated HTTPX fallback.

This split avoids a risky application-wide HTTP-client migration while removing the deprecation path actually exercised by tests.

### Executive summary: monorepo tooling and lifecycle policy

| Boundary          | Decision                                                                                                 | Why                                                                                                                                                                    | Executable evidence                                   |
| ----------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Package manager   | Pin `pnpm@10.34.5`                                                                                       | Current pnpm 10 maintenance release while preserving the existing lockfile major                                                                                       | `packageManager`; `test_node_tooling_contract.py`     |
| Script runtime    | Let pnpm download and use `node@24.19.0` through `devEngines.runtime`                                    | Tailwind's current Node adapter emits `DEP0205` under Node 26; Node 24 is a maintained LTS and is warning-free for this build                                          | `pnpm install`; uncached `pnpm build`                 |
| Oxide fallback    | Deny `@tailwindcss/oxide@4.1.12` postinstall                                                             | The reviewed script performs a registry download and archive extraction only when the locked optional binary is missing; direct load and production build already pass | `pnpm.ignoredBuiltDependencies`; lock/version checker |
| Resolver fallback | Deny `unrs-resolver@1.11.1` postinstall                                                                  | The reviewed checker can invoke npm or download a native binding; the locked optional binding already loads and lint/build pass                                        | `pnpm.ignoredBuiltDependencies`; lock/version checker |
| API build         | Remove the echo-only package build task                                                                  | FastAPI is a runtime service and produces no build artifact; claiming a successful build created a Turborepo cache warning and false evidence                          | absence asserted by architecture test                 |
| GitHub Actions    | Full-SHA pins for checkout v7.0.1, setup-node v7.0.0, setup-python v7.0.0, and pnpm/action-setup v6.0.10 | These reviewed releases use Node 24 internally and eliminate GitHub's Node 20 action-runtime annotation                                                                | architecture test, Pinact, Zizmor, native CI          |

No lifecycle script is silently approved. Future lock changes remain denied by pnpm and fail `pnpm run check:dependency-build-policy` until the exact new version, package manifest, lifecycle entrypoint, support-package implementation, and pending-build state are reviewed.

The Node 26 warning is tracked upstream at https://github.com/tailwindlabs/tailwindcss/issues/19893. Remove the managed Node 24 constraint only after a stable Tailwind release replaces `module.register()` and an uncached Node 26 build is warning-free; do not suppress `DEP0205`.

### Extension and exception discipline

Probable extensions must cross named ports/capability registries rather than adding sibling modules indefinitely. Every exception is exact, risk-bearing, no-growth, and has a refactoring trigger. Generated/vendor/migration/resource paths are declared explicitly; they do not silently weaken runtime rules.

<!-- PORTFOLIO-CONSTITUTION:END -->

### CV sync persistence

LinkedIn sync preserves curated `projects`, `awards` and `date_precision_note` when the typed provider profile omits those fields. An explicitly supplied empty list or null replaces that section; Pydantic's `model_fields_set` defines this distinction. The merge creates a newly validated profile and leaves the provider object unchanged.

The existing Pydantic serializer/validator owns URL, enum and date conversion ([serialization](https://docs.pydantic.dev/latest/concepts/serialization/), [model validation](https://docs.pydantic.dev/latest/concepts/models/)). Generic recursive date guessing is removed so date-looking text stays text. CVService serializes the full profile before writing a same-directory temporary file, then atomically replaces storage. Failed persistence retains the previous file and cache and returns a failed sync. Offline tests in `apps/api/tests/test_cv_sync.py` verify omitted/explicit fields, typed storage roundtrip and failed replacement; [#107](https://github.com/googa27/main_website/issues/107) tracks this correction.
