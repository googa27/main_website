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

### Responsive site navigation

`Navigation.tsx` owns the existing responsive links and a mobile disclosure,
using React state and native button/link behavior. The named button exposes
`aria-expanded` and `aria-controls`; Escape closes and restores button focus.
Leaving navigation with Tab or selecting a link closes it. Desktop navigation
keeps its existing layout. This follows the [WAI disclosure navigation pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation/),
without imposing menu-widget keyboard behavior on ordinary site links.

`tests/e2e/mobile-navigation.mjs` checks actual browser interactions against a
built static site using a caller-provided Playwright Page. It is separate from
the frontend `pnpm test` placeholder and does not add a runtime dependency.
See `tests/e2e/README.md` for execution and evidence boundaries; browser,
rendered-style and assistive-technology results must be recorded separately.

### Executive summary: optional API time and HTTP clients

- **UTC timestamps:** `apps/api/app/core/time.py::utc_now` is the single clock factory for generated API timestamps. It returns aware UTC values; ORM timestamp columns declare `DateTime(timezone=True)`.
- **Legacy data:** the repository has Alembic scaffolding but no revision baseline. `UTCDateTime` therefore interprets existing naive timestamps as UTC and restores aware UTC values after database reads rather than claiming an unexecuted production migration. PostgreSQL preserves timezone semantics directly; SQLite may discard offsets internally, but the application boundary restores them before consumers or serializers observe the value.
- **HTTP ownership:** `httpx` remains the runtime client used by the GitHub adapter. `httpx2` is development-only and backs Starlette/FastAPI `TestClient`, as recommended by current Starlette documentation. HTTPX2 2.12.0 is the Pydantic-maintained BSD-3-Clause distribution ([source and release](https://github.com/pydantic/httpx2/releases/tag/v2.12.0), [package metadata](https://pypi.org/project/httpx2/2.12.0/)); it selects exact HTTPcore2 2.12.0. Starlette 1.6.0 [explicitly selects HTTPX2](https://github.com/Kludex/starlette/blob/1.6.0/starlette/testclient.py#L29-L48) and warns on the canonical HTTPX fallback. This development-only upgrade resolves the stale test-transport audit findings tracked in [#106](https://github.com/googa27/main_website/issues/106); runtime HTTP ownership is unchanged.
- **Fail-closed verification:** API tests promote Python and Starlette deprecations to errors. `apps/api/tests/test_datetime_contracts.py` forbids `datetime.utcnow`, verifies timezone-aware ORM declarations and CV defaults, and proves TestClient selected HTTPX2 rather than its deprecated HTTPX fallback.

This split avoids a risky application-wide HTTP-client migration while removing the deprecation path actually exercised by tests.

### Executive summary: monorepo tooling and lifecycle policy

| Boundary           | Decision                                                                                                 | Why                                                                                                                                                                    | Executable evidence                                   |
| ------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Package manager    | Pin `pnpm@10.34.5`                                                                                       | Current pnpm 10 maintenance release while preserving the existing lockfile major                                                                                       | `packageManager`; `test_node_tooling_contract.py`     |
| Script runtime     | Let pnpm download and use `node@24.19.0` through `devEngines.runtime`                                    | Tailwind's current Node adapter emits `DEP0205` under Node 26; Node 24 is a maintained LTS and is warning-free for this build                                          | `pnpm install`; uncached `pnpm build`                 |
| Oxide fallback     | Deny `@tailwindcss/oxide@4.1.12` postinstall                                                             | The reviewed script performs a registry download and archive extraction only when the locked optional binary is missing; direct load and production build already pass | `pnpm.ignoredBuiltDependencies`; lock/version checker |
| Resolver fallback  | Deny `unrs-resolver@1.12.2` postinstall                                                                  | The reviewed local wrapper and napi-postinstall 0.3.4 can invoke npm or download a native binding; require the locked optional binding to load and lint/build to pass                                        | `pnpm.ignoredBuiltDependencies`; lock/version checker |
| API build          | Remove the echo-only package build task                                                                  | FastAPI is a runtime service and produces no build artifact; claiming a successful build created a Turborepo cache warning and false evidence                          | absence asserted by architecture test                 |
| GitHub Actions     | Full-SHA pins for checkout v7.0.1, setup-node v7.0.0, setup-python v7.0.0, and pnpm/action-setup v6.0.10 | These reviewed releases use Node 24 internally and eliminate GitHub's Node 20 action-runtime annotation                                                                | architecture test, Pinact, Zizmor, native CI          |
| Dependency updates | Discover npm from the repository root and group React runtime/declaration packages                       | The workspace owns one root lock; child-directory updates cannot independently reconcile coupled importers                                                             | parsed Dependabot architecture regression             |

No lifecycle script is silently approved. Future lock changes remain denied by pnpm and fail `pnpm run check:dependency-build-policy` until the exact new version, package manifest, lifecycle entrypoint, support-package implementation, and pending-build state are reviewed.

Resolver 1.12.2 uses `node postinstall.js`, calling the published
`napi-postinstall` API. The deny-only policy binds that wrapper separately from
the support package manifest, CLI and complete executable `lib/*.js` tree.
The support update adds platform detection; its download/install and fallback
implementations remain byte-identical to 0.3.3. The resolver now limits its
runtime install fallback to WebContainer, so ordinary Node fails if neither
the native nor WASI binding loads. Frozen installation, direct native binding
load, lifecycle policy, lint, typecheck and production build remain acceptance
gates; policy metadata does not prove those executions. Sources:
[resolver 1.12.2](https://registry.npmjs.org/unrs-resolver/1.12.2) and
[napi-postinstall 0.3.4](https://registry.npmjs.org/napi-postinstall/0.3.4).
The synthetic temporary-layout regression proves that altered wrapper, support
CLI and support-library bytes are refused, along with lock and pending-build
drift. It does not execute an installer or substitute for real package review.

The Node 26 warning is tracked upstream at https://github.com/tailwindlabs/tailwindcss/issues/19893. Remove the managed Node 24 constraint only after a stable Tailwind release replaces `module.register()` and an uncached Node 26 build is warning-free; do not suppress `DEP0205`.

Dependabot's single npm entry starts at `/`, where `pnpm-lock.yaml` owns the
workspace. Its React group spans `react`, `react-dom`, `@types/react`, and
`@types/react-dom` without restricting production or development dependencies;
the pip updater, weekly cadence, seven-day cooldown, and security updates remain
enabled. The parsed configuration regression checks that ownership rather than a
group label or YAML formatting.

The updater also groups the TypeScript-ESLint parser and plugin, because the
plugin's same-family parser peer must advance together. Only semver-major
version updates for `eslint` and `typescript` are held while current web plugin
peers and compiler API consumers reject those proposals. Existing accepted
major versions remain unchanged, including UI ESLint 10. Remove each hold when
its documented compatibility gate passes. There are no name-only or explicit
version-range exclusions. Dependabot ignores these update-type filters for
security-only jobs; the parsed regression rejects broader filters and preserves
the root workspace, React group, weekly schedule and seven-day cooldown.
This config change is not proof that the full scheduled updater recovered;
keep issue #136 open until that actual workflow succeeds.
[Upstream security filtering](https://github.com/dependabot/dependabot-core/blob/6634a4a4b6e203f3afcd302052839d290e6e61bf/common/lib/dependabot/config/ignore_condition.rb#L40-L46)
and its [regression](https://github.com/dependabot/dependabot-core/blob/6634a4a4b6e203f3afcd302052839d290e6e61bf/common/spec/dependabot/config/ignore_condition_spec.rb#L336-L342)
record the distinction between update-type and explicit version filters.


Web and UI resolve one reviewed React cohort: React and React DOM 19.2.8,
`@types/react` 19.2.18, and `@types/react-dom` 19.2.7. The architecture
regression reads both manifests and the parsed root lock, so a broad declaration
range cannot silently leave either importer on older React types.

TypeScript remains on major 5 because the locked TypeScript-ESLint 8.63.0 peer
range is `>=4.8.4 <6.1.0`, and TypeScript 7.0 does not yet provide the stable
programmatic API required by tooling consumers. Revisit the compiler only when
those consumers and peer ranges support the candidate and lint, typecheck, and
build pass. Node and its declarations remain on major 24 until the Tailwind
removal trigger above is satisfied and the managed install plus lifecycle,
lint, typecheck, and build gates pass.

### Extension and exception discipline

Probable extensions must cross named ports/capability registries rather than adding sibling modules indefinitely. Every exception is exact, risk-bearing, no-growth, and has a refactoring trigger. Generated/vendor/migration/resource paths are declared explicitly; they do not silently weaken runtime rules.

<!-- PORTFOLIO-CONSTITUTION:END -->

### CV sync persistence

LinkedIn sync preserves curated `projects`, `awards` and `date_precision_note` when the typed provider profile omits those fields. An explicitly supplied empty list or null replaces that section; Pydantic's `model_fields_set` defines this distinction. The merge creates a newly validated profile and leaves the provider object unchanged.

The existing Pydantic serializer/validator owns URL, enum and date conversion ([serialization](https://docs.pydantic.dev/latest/concepts/serialization/), [model validation](https://docs.pydantic.dev/latest/concepts/models/)). Generic recursive date guessing is removed so date-looking text stays text. CVService serializes the full profile before writing a same-directory temporary file, then atomically replaces storage. Failed persistence retains the previous file and cache and returns a failed sync. Offline tests in `apps/api/tests/test_cv_sync.py` verify omitted/explicit fields, typed storage roundtrip and failed replacement; [#107](https://github.com/googa27/main_website/issues/107) tracks this correction.

### Python tooling and asynchronous CV synchronization

Ruff 0.16 uses an explicit rule policy in the API pyproject. Established correctness
checks remain, with focused import/type modernization, mutable-default and blocking
I/O checks. FastAPI dependency markers, public enum string representation and one
Alembic bootstrap import have narrow documented exceptions. Existing optional-provider
and application fallback contracts remain intact.

The CV public import remains `app.services.cv`. Its package separates orchestration,
typed atomic storage and the existing pure MDX renderer; each module is below 500
lines and the old 584-line exception is retired. A per-instance thread lock serializes
read/merge/atomic-write/cache publication. Cancelling a request after its storage
transaction is scheduled may still complete that transaction; subsequent operations
observe its completed state, preserving omitted curated sections and cache/disk
agreement. Provider HTTP requests happen outside the storage lock.

LinkedIn acquisition uses the already declared HTTPX async client with one 30-second
acquisition deadline and finite connection/read/write/pool timeouts. Optional-section
failures retain earlier successful sections. Tests use synthetic HTTPX transports
and controlled storage-thread events, including a cancelled first writer followed
by a second update. No live provider or private data is needed.

This follows HTTPX's [async client lifecycle](https://www.python-httpx.org/async/)
and [phase timeout](https://www.python-httpx.org/advanced/timeouts/) contracts,
with Python's [task deadlines and I/O offloading](https://docs.python.org/3.12/library/asyncio-task.html).
HTTPX is already a runtime dependency, so the adapter needs no additional client
library. Redirect behavior is retained, with a synthetic cross-origin redirect
test verifying that authorization is not forwarded to the new origin. Domain
code owns curated-field merging; the standard library owns locking and scheduling.

The installed API gate builds a wheel with Setuptools' explicit package-data rule
for the reviewed CV JSON, installs only the runtime package into a separate
environment and runs `scripts/check_installed_api.py` with an isolated interpreter
outside the checkout. It verifies application imports, typed public fixture export
and contact-redacted AI context. This protects against [#113](https://github.com/googa27/main_website/issues/113),
where editable imports passed while the wheel omitted the startup fixture. Mypy's
existing configuration excludes only generated `build/` copies to avoid duplicate
module discovery after an artifact build; new export owners now opt into type checking while legacy exclusions remain.
The static mount is also module-relative. The packaging rule uses maintained
[Setuptools package-data support](https://setuptools.pypa.io/en/latest/userguide/datafiles.html),
and the real installed-wheel gate provides the regression oracle.

### CV completion and retry ownership

The CV orchestration passes `defer_completion=True` to the existing provider sync
method and acknowledges completion only after atomic storage and cache publication
succeed in the same worker transaction. A failed save leaves ordinary retries
eligible. Cancellation during acquisition records no completion; cancelling an
already scheduled worker may still complete persistence and acknowledgement together.
Failed older requests never reset another successful request's completion.

Direct `LinkedInService.sync_profile_data` callers retain acquisition-level completion
by default. Persistence owners that defer it must call `mark_sync_completed` after
success. A provider lock protects completion publication and status snapshots, and
timestamps never move backward even if wall-clock readings do. This in-process
throttle does not claim cross-process coordination or durable scheduling. Actual
provider interaction and controlled thread tests protect [#114](https://github.com/googa27/main_website/issues/114).

### Public CV export and curated read boundaries

[CV_EXPORTS.md](CV_EXPORTS.md) records the library decisions, installed CLI/API, date precision, optional capabilities and exact retained-draft disposition for issue #116. `CVProfile` feeds immutable typed JSON Resume projection, fixed offline schema validation and optional text-only ReportLab rendering. Separate modules own each responsibility; the service facade owns asynchronous orchestration. The renderer escapes all content and uses only packaged fonts. A process-local lock covers its complete ReportLab operation, including paragraph work and final font subsetting, because the registered TTFont face parser has a shared mutable cursor. Context-managed release protects exception recovery; asynchronous service calls keep both rendering and lock waiting in worker threads. This bounds PDF throughput to one render per process without blocking the event loop; independent processes own independent state. The CLI renders before atomic output replacement. Source and installed-wheel gates protect the official schema and license resources as well as the public fixture.

Curated project fallback is a pure ordered projection with explicit source, metric availability and timestamp semantics. Its URL-derived negative IDs are display identities, not provider keys. GET performs database reads or current-fixture reads only; existing explicit sync remains separate. Static `/cv/preview` composes existing About content and exposes downloads only for a configured optional API, without build-time acquisition.

### Shared local hook toolchain

[Issue #118](https://github.com/googa27/main_website/issues/118) replaces the archived Prettier mirror and divergent isolated Ruff/Mypy/ESLint environments with [repository-local pre-commit hooks](https://pre-commit.com/#repository-local-hooks). The existing activated API environment owns Python tool versions; the frozen pnpm workspace owns ESLint/Prettier and shared configs. This follows [Prettier's workspace hook guidance](https://prettier.io/docs/precommit). Ruff and Prettier receive scoped filenames, while Mypy/ESLint run their complete configured project gates when related files change. The API package scripts now use Ruff formatting and expose the existing Mypy check. The hook runner does not install Git hooks or dependencies automatically. Explicit setup and runner commands are in AGENTS.md.

Ruff discovers the closest configuration for each supplied API filename. Do not pass `--config apps/api/pyproject.toml` from the repository root: Ruff documents that explicit configuration paths resolve relative patterns against the current working directory, which changes the API's per-file exemptions and import classification. [Ruff configuration discovery](https://docs.astral.sh/ruff/configuration/) is used and native all-file hook execution verifies it.

## Python dependency minimum policy

The private architecture checker uses PyPA packaging 26.3 Requirement, canonical names and Version ordering. `_SECURITY_MINIMUMS` in `tests/architecture/test_dependency_security_floors.py` owns security minima; application manifests own selected versions. A newer synchronized stable exact pin can meet a minimum without proving API compatibility. Consumer tests and review remain required before selecting it. AnyIO is protected at the upstream patched minimum 4.14.2, independently of its selected 4.15.1 pin. Copied-manifest controls reject a synchronized downgrade to 4.14.1 and accept a newer synchronized 4.15.1 pin.

Protected pins reject ambiguous/conditional forms, extras, URL sources and prerelease/dev/local versions. Duplicate normalized names fail before full runtime/development manifest comparison. Requirements files permit comments/blank lines and the single existing development `-r requirements.txt` include; arbitrary recursive includes are not traversed. Real copied-manifest controls demonstrate newer pins, below-floor refusal, duplicates, malformed declarations and full parity. Unprotected-package parity controls select exactly one current declaration by canonical name, prove that the parsed constraint changes in only the requirements copy, and require the parity-specific rejection. The same controls exercise a synthetic selected version so ordinary Ruff/FastAPI updates cannot turn their mutation into a silent no-op.

Run `python -m pip install -r requirements-architecture.txt pytest`, then `python -m pytest tests/architecture` and `python scripts/check_portfolio_architecture.py`. The CI test job uses that declared setup after its API profile. packaging is governance-only, explicitly declared rather than inherited from pip/pytest. The pinned PyPA release supports Python >=3.9 and is licensed Apache-2.0 OR BSD-2-Clause; primary contracts are [Requirement](https://packaging.pypa.io/en/stable/requirements.html), [Version](https://packaging.pypa.io/en/stable/version.html) and [release metadata](https://pypi.org/project/packaging/26.3/).

Selected IDNA 3.19 and Mako 1.4.1 retain the independent security minimums. `apps/api/tests/test_dependency_consumers.py` exercises ContactCreate/EmailStr, email-validator and runtime HTTPX request preparation with Unicode, ASCII and invalid/noncanonical domains. EmailStr retains normalized Unicode; email-validator's ASCII email and HTTPX's raw host expose wire normalization. HTTPX bypasses IDNA for entirely ASCII hosts, so its canonical-label negative includes a Unicode label. Socket/DNS operations are refused by these tests.

The same owner uses actual installed Alembic generic and repository revision templates to generate temporary revisions and verify metadata, upgrade/downgrade content and Python syntax, without database access, env.py, autogeneration or post-write hooks. It verifies that the Mako distribution does not own the stray top-level tools package fixed in 1.4.1. Policy controls normalize owned copies to minimum pins independently of selected versions; actual repository parity remains a separate test. Primary behavioral references are the [IDNA 3.19 history](https://raw.githubusercontent.com/kjd/idna/v3.19/HISTORY.md) and [Mako 1.4.1 changelog](https://raw.githubusercontent.com/sqlalchemy/mako/rel_1_4_1/doc/build/changelog.rst). These controls do not establish live provider, DNS, database or deployment behavior.


AnyIO 4.15.1 is explicitly constrained in both runtime manifests as an existing
transitive async dependency; dev/PDF requirements inherit the base declaration.
[Upstream metadata](https://pypi.org/pypi/anyio/4.15.1/json) declares Python >=3.10
and MIT licensing, compatible with this API's Python >=3.12 profile. The selected
version was installed by the successful Python 3.12 backend job in
[run 35538162830](https://github.com/googa27/main_website/actions/runs/35538162830).
It exceeds the 4.14.2 fixes for
[TLS hostname handling](https://github.com/agronholm/anyio/security/advisories/GHSA-82r6-8w77-94w6)
and [process-worker stderr blocking](https://github.com/agronholm/anyio/security/advisories/GHSA-5p39-cfhj-2xmp).
That run's full OSV scan independently inferred vulnerable AnyIO 4.9.0; it does
not prove the tested or deployed application installed that version. The exact
pin follows the manifest convention and makes this security constraint explicit,
but does not establish what a fresh resolver will select or that the full scan
will pass. Recheck backend tests, base/dev/PDF pip-audit and the real full OSV
scan; retain any resolution failure without suppressing either advisory or
transitive scanning.
