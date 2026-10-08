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

### Optional API database driver selection

The API declares `psycopg2-binary`. A `DATABASE_URL` with the plain `postgresql`
scheme therefore selects `postgresql+psycopg2` explicitly before engine
construction ([#192](https://github.com/googa27/main_website/issues/192)).
SQLAlchemy's maintained `make_url` and immutable `URL.set` retain escaped
credentials, query parameters and other components; explicit drivers and other
backends retain their supplied selection and actual import/refusal behavior.
This avoids relying on the implicit PostgreSQL default, which
[changed in SQLAlchemy 2.1](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html#default-postgresql-driver-changed-to-psycopg-psycopg-3).
The five real isolated engine-import controls in
`apps/api/tests/test_database_driver_selection.py` also run as a standalone
unittest suite against normally installed dependency proposals. They never open
a database connection. Import compatibility does not accept a dependency
cohort, live PostgreSQL operations, migrations or deployment.

### Executive summary: monorepo tooling and lifecycle policy

The optional API selects Mako 1.4.3 for Alembic's existing revision templates
([#193](https://github.com/googa27/main_website/issues/193)). The separate security
minimum is 1.4.2, the patched boundary in
[GHSA-5639-2j2p-m4mx](https://github.com/sqlalchemy/mako/security/advisories/GHSA-5639-2j2p-m4mx).
Literal tests reject the affected 1.4.1 release and accept 1.4.2/1.4.3 without
deriving that oracle from the minimum map. The structured library selection
must also match both runtime manifests; a version-only bump leaves that
contract stale.

The maintained [1.4.3 release](https://github.com/sqlalchemy/mako/releases/tag/rel_1_4_3)
includes the upstream test-portability correction after the 1.4.2 traversal
repair. Existing consumer tests render both installed Alembic and repository
templates into temporary revisions and check Python syntax, revision IDs,
upgrade/downgrade contents, and distribution ownership. They do not run
`env.py`, connect to a database, prove a deployed vulnerable template route,
or substitute for actual Windows or full dependency-security verification.

| Boundary           | Decision                                                                                                 | Why                                                                                                                                                                    | Executable evidence                                   |
| ------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Package manager    | Pin `pnpm@10.34.5`                                                                                       | Current pnpm 10 maintenance release while preserving the existing lockfile major                                                                                       | `packageManager`; `test_node_tooling_contract.py`     |
| Script runtime     | Let pnpm download and use `node@24.19.0` through `devEngines.runtime`                                    | Tailwind's current Node adapter emits `DEP0205` under Node 26; Node 24 is a maintained LTS and is warning-free for this build                                          | `pnpm install`; uncached `pnpm build`                 |
| Oxide native load  | Accept `@tailwindcss/oxide@4.3.3` without an install hook after exact review                             | The published manifest has no install hook; the reviewed loader selects a same-version locked optional native binding without the former registry-download postinstall | manifest/loader hashes; native load and build         |
| Resolver fallback  | Deny `unrs-resolver@1.12.2` postinstall                                                                  | The reviewed local wrapper and napi-postinstall 0.3.4 can invoke npm or download a native binding; require the locked optional binding to load and lint/build to pass  | `pnpm.ignoredBuiltDependencies`; lock/version checker |
| API build          | Remove the echo-only package build task                                                                  | FastAPI is a runtime service and produces no build artifact; claiming a successful build created a Turborepo cache warning and false evidence                          | absence asserted by architecture test                 |
| GitHub Actions     | Full-SHA pins for checkout v7.0.1, setup-node v7.0.0, setup-python v7.0.0, and pnpm/action-setup v6.0.10 | These reviewed releases use Node 24 internally and eliminate GitHub's Node 20 action-runtime annotation                                                                | architecture test, Pinact, Zizmor, native CI          |
| Dependency updates | Discover npm from the repository root and group React runtime/declaration packages                       | The workspace owns one root lock; child-directory updates cannot independently reconcile coupled importers                                                             | parsed Dependabot architecture regression             |

No lifecycle script is silently approved. The gate pins Oxide's 4.3.3 manifest and loader bytes, rejects newly added install hooks or mixed-version optional bindings, and continues to deny the resolver's reviewed postinstall. A future lock change fails until its version, install behavior, native bindings and pending-build state are reviewed; a package with a lifecycle script needs its own explicit deny decision and script-byte review.

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

Web and UI resolve one reviewed React cohort: React and React DOM 19.3.0,
`@types/react` 19.3.0, and `@types/react-dom` 19.3.0. The architecture
regression reads both manifests and the parsed root lock, so a broad declaration
range cannot silently leave either importer on older React types. The cohort
identifies declared and installed public packages. Next.js App Router uses its
own bundled React canary; its React peer range accepts this cohort, but that
alone does not establish rendering compatibility. Accept the cohort only after
frozen installation, web/UI typecheck and lint, an uncached build, and actual
hydration/navigation/browser comparisons. No new React API is adopted here.
See the [React 19.3 release](https://react.dev/blog/2026/09/09/react-19-3)
and [Next.js installation contract](https://nextjs.org/docs/app/getting-started/installation).

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

The gate also retains the cause of a failed child invocation ([#191](https://github.com/googa27/main_website/issues/191)).
A nonzero exit keeps its actual exit code; an actual 30-second timeout keeps
`TimeoutExpired` and its deadline. Each `stdout` and `stderr` diagnostic contains
the last 4096 captured bytes as UTF-8 text with replacement for invalid bytes,
the original byte count and a truncation flag. An interpreter launch error keeps
its error type and errno. Successful output, isolated execution, temporary cwd
and the supplied virtual-environment symlink identity are preserved. A zero-exit
child must emit valid UTF-8 on both streams; invalid bytes fail with
`UnicodeDecodeError` and the same bounded diagnostics before any successful
output is printed.
Python's maintained [subprocess API](https://docs.python.org/3.12/library/subprocess.html)
owns execution and timeout handling. These report bounds do not limit the total
output buffered by `subprocess.run`. The fixed probe uses the reviewed public
fixture; the wrapper does not print environment or private fixture metadata.
Real finite child tests exercise the reporting boundary without mocking process
execution. A useful traceback is diagnosis evidence; dependency-version
compatibility still needs its own installed consumer checks.

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

The same owner uses actual installed Alembic generic and repository revision templates to generate temporary revisions and verify metadata, upgrade/downgrade content and Python syntax, without database access, env.py, autogeneration or post-write hooks. The structured selected-version map in the machine contract owns the current Alembic, Mako and SQLAlchemy pins, and the manifest-parity test checks that map. [Alembic release metadata](https://pypi.org/pypi/alembic/1.20.0/json) states the SQLAlchemy minimum for the selected release; task evidence checked installed distribution metadata and RECORD. This compatibility statement is not a separate architecture gate. `apps/api/tests/test_dependency_consumers.py` verifies that the Mako distribution does not own the stray top-level tools package reported in the linked Mako changelog. Policy controls normalize owned copies to minimum pins independently of selected versions; actual repository parity remains a separate test. The machine-readable selected sentence names the three packages without version digits; only its structured version map is checked against both runtime manifests. Alembic is not assigned a security minimum because no advisory floor is claimed. Primary behavioral references are the [IDNA history](https://raw.githubusercontent.com/kjd/idna/v3.19/HISTORY.md), [Mako changelog](https://raw.githubusercontent.com/sqlalchemy/mako/rel_1_4_1/doc/build/changelog.rst), and [Alembic release notes](https://github.com/sqlalchemy/alembic/releases/tag/rel_1_20_0). These controls do not establish live provider, DNS, database or deployment behavior.

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

## Brace-expansion consumer security route

[Issue #194](https://github.com/googa27/main_website/issues/194) updates the existing
brace-expansion override route to 1.1.21 and 5.0.12. The installed minimatch 3.1.5
parent accepts `^1.1.7`; minimatch 10.2.5 and 10.2.6 accept `^5.0.5` and `^5.0.8`.
The selected patched versions satisfy these actual parent ranges without changing
minimatch versions. The retained v2 override moves to 2.1.7, but no installed v2
or v3 consumer acceptance is claimed. The pre-existing v4-to-v5 override boundary
is retained; no installed v4 parent was found in this cohort.

The maintained package is MIT licensed. The published 5.0.12 distribution retains
CommonJS and ES-module exports and supports Node `20 || >=22`, including the
managed Node 24.19.0. Published tarball integrity and manifests were checked;
neither selected branch adds an install lifecycle hook. This uses the upstream
parser repair rather than a custom brace parser. The selected cohort and exact
consumer list live in `architecture.brace_expansion_policy`; PyYAML parses the
lockfile package and snapshot sections for the architecture gate. A new parent
or branch requires a reviewed selection and corresponding executable consumer
coverage. No vulnerability suppression or scanner bypass is added.

`pnpm run check:dependency-build-policy` now also runs the installed consumer tests
in `tests/node/brace-expansion.test.mjs`. They use actual minimatch public
`braceExpand`, `Minimatch`, and CommonJS/modern ES-module entrypoints. Literal
ordinary expansion and matching controls accompany the upstream advisory inputs:
[recursive comma parsing](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-6j4f-fj2g-mc7p),
[both nesting sites](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-qhr7-859c-m2p7),
and [excessive rewrite preservation](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-q2hr-2g5m-vwhr).
The argument-array input exceeds minimatch's length limit and therefore tests its
resolved brace-expansion public export directly. Parser payloads used through
minimatch remain below that limit. Excessive rewrite behavior uses the upstream
literal-output contract rather than a wall-clock performance assertion. These are
local toolchain checks, not evidence of an exploitable deployment, live service,
or scientific result. The full frozen install, lifecycle, frontend/API/architecture
gates, all Python audits and unsuppressed OSV scan remain required.

### Indexed source-map resource bounds

The structured `architecture.source_map_policy` owns the reviewed source-map-js
selection and both actual PostCSS/Tailwind parents. The
[upstream advisory](https://github.com/7rulnik/source-map-js/issues/76) identifies
line-padding past the generated content in `SourceNode.fromStringWithSourceMap`.
The maintained 1.2.2 release stops that padding once the content is exhausted.
The same release validates non-negative safe integer section offsets, caps
individual and accumulated nested section lines, and rejects excessive offsets.

The required dependency policy command exercises the real resolved library from
each parent: generator/consumer/SourceNode round trips, indexed generated-line offsets,
large admitted offsets with literal generated-code preservation, and refusal
of invalid or excessive individual and accumulated nested offsets. Exact
section-start lookup and nonzero section-column correctness remain a distinct
pre-existing upstream limitation tracked in [issue204](https://github.com/googa27/main_website/issues/204),
separately from the security repair. A test-only public `add` circuit breaker prevents the old library
from consuming unbounded resources during reproduction; it delegates every
accepted call and is never installed as a production workaround. Full frontend
build consumers and the unsuppressed scanner remain required. These controls do
not establish a deployed vulnerable input path or a live exploit.

## Maintained native SVG dependency

[Issue #197](https://github.com/googa27/main_website/issues/197) selects Sharp
0.35.5 and its matching native packages through the maintained Next 16.3.8 parent.
The maintained release fixes
[GHSA-wq5f-xc86-pv6w](https://github.com/lovell/sharp/security/advisories/GHSA-wq5f-xc86-pv6w)
and ships libvips 8.18.7 with librsvg 2.63.2. The manifest override and frozen
lock retain the complete published optional dependency cohort. Sharp and its
GNU binding are Apache-2.0 licensed; the prebuilt libvips package is
LGPL-3.0-or-later. Their reviewed manifests have no install lifecycle hooks.
The maintained runtime loader loads the selected prebuilt native module or
fails with diagnostics; no new download wrapper or custom renderer is added.

`architecture.sharp_policy` records the reviewed parent, published tarball
integrities and GNU asset hashes. The required dependency policy command
executes the actual Sharp export resolved by Next. Hand-derived red pixels,
resize, PNG roundtrip, malformed SVG and explicit pixel-limit controls preserve
public rendering behavior. The exported librsvg version comes from package
metadata; separate controls compare the installed binding, shared library and
version file with independently verified published bytes and require the two
binaries to appear in the consumer process mappings. They prevent accepting an
ambient or substituted GNU renderer merely from a version string.

These gates verify the local GNU Linux x64 dependency and public library
consumer. They do not reproduce the use-after-free exploit, verify other
platform native execution or establish a deployed image endpoint. The static
frontend's unoptimized image behavior is unchanged. Full source, frontend, API,
architecture, normal installed-package and unsuppressed security gates remain
required; other existing security owners remain separate.

## Maintained Next security cohort

Next and its ESLint config resolve as one 16.3.8 cohort, with a pnpm floor preventing older 16.x consumers from returning. The selected release repairs the six 16.3.8 advisory ranges and includes the next/og 16.3.6 repair. Canonical advisory IDs, exact independently published GNU compiler identities, optional platform selections and executable acceptance live in `next_security_policy` in ARCHITECTURE.yaml. Upstream pages currently contain placeholder patch fields; the maintained [16.3.8 release](https://github.com/vercel/next.js/releases/tag/v16.3.8), published registry identities and full OSV affected ranges establish the selected boundary.

The required Next control starts the actual declared Turbopack developer server on an ephemeral loopback listener. A local MCP initialization succeeds; foreign/opaque origins are refused, and lookalike paths do not expose the MCP response. Explicit foreign-origin requests already failed on the prior release; only the exact-path case is the observed middleware regression. The test stops the real CLI and verifies observed owned children are absent. A shared process observer tolerates only missing proc entries during exit races; cleanup still awaits the real exit. A naturally exited real child exercises that regression. Its startup/request deadlines are bounded test guards, not security performance claims. GNU compiler hashes are derived from independently published tarballs, and live process mappings plus a literal TypeScript result verify the actual Next compiler. Other platforms are locked but unexecuted.

The frontend retains static export with unoptimized images. This source has no enabled draft-cache previews, ISR server, dynamic metadata image routes or attacker-controlled next/og renderer. Version/lock controls and the full unsuppressed dependency scan cover the owned advisory cohort; they do not demonstrate a deployed exploit or a live server. Existing full frontend/architecture/backend and fresh normal installed-API gates remain required. Next's generated web agent guidance is retained for version-accurate documentation discovery; it grants no additional authority over the user or root constitution. Unrelated Node 26/TypeScript 7 migrations, braces issue 195, source-map correctness issue 204, documentation issues 200/202 and broader issue 136 remain separate.
