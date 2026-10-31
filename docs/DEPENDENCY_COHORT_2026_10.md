# October 2026 remaining dependency proposals

This bounded local successor starts at main `0f0bf1a467ffff15506c762331905e2ac2a40032`.
It preserves original accepted proposal heads in Git ancestry. Intermediate merge
commits are integration history, not individually accepted or verified candidates.
The final tree must pass the existing gates before publication. Issues
[#136](https://github.com/googa27/main_website/issues/136) and
[#263](https://github.com/googa27/main_website/issues/263) remain the owners.

| Proposal | Selected target or disposition | Original head |
| --- | --- | --- |
| #253 | FastAPI 0.143.0 superseded by #268; Dependabot already closed it unmerged | `3977e61c2d98534b6b3fb821c80f94b176ee7626` |
| #254 | Pydantic 2.14.0 superseded by #266; Dependabot already closed it unmerged | `3d9dfc8a74fe364a7a650b80880052dc96b6f57f` |
| #260 | Hold Prettier 3.9.10; retain 3.9.8 | `f4e42bf06346faa799e9116fb663ee85ef499e24` |
| #261 | @types/node 24.19.2; retain managed Node 24.19.0 | `70342b5ec64083c2c13d6645d582f0d64dbec0d0` |
| #264 | Alembic 1.20.1 | `3b820f168df8316a608d2057e589c0f67f0921f5` |
| #265 | Ruff 0.17.2; existing explicit rule selection and exclusions | `3102bb2f628d0fd221c71b8d738f11ebea1518d4` |
| #266 | Pydantic 2.14.1, exact pydantic-core 2.50.1 | `a9ae5d1f95c5089a2d35239a1d6c4ace30e044d8` |
| #267 | React/DOM 19.3.1, declarations 19.3.0 in web and UI | `44f84a8a649b7d38e757024f424066ab3372fd37` |
| #268 | FastAPI 0.162.0 | `96817ea9c14409d937c46ffef9eb0c97e41d7897` |
| #269 | Development HTTPX2/HTTPcore2 2.16.0; runtime HTTPX stays 0.28.1 | `f2b508ba45b2b2b5ca7aa2eb3ed75075f0ba329b` |
| #270 | Next 16.4.3 and its same-version optional compilers | `4e4280019ef5232564973755c8c69d9e0fa4eda0` |
| #271 | eslint-config-next/plugin 16.4.3; retain supported existing transitive selections | `c90bce2d4c2fae8d5b4e79952556ee91e7f61f71` |

All ten currently open targets were published more than seven days before the
2026-10-31 review. This does not make incompatible versions acceptable. The
existing root weekly updater configuration, major-only holds, seven-day cooldown,
strict peers, managed Node, pnpm and security-update behavior stay unchanged.
TypeScript ESLint 8.72.1 was published October 26 and is still inside the cooldown;
8.72.0 remains selected. TypeScript 7 and Node/types 26 remain outside the documented
compiler/peer/runtime acceptance boundary.

## Content and compatibility decisions

Prettier 3.9.10's actual native #260 quality run fails the mathematical-content
controls. Both installed formatter entry points change `Let $r^*$ and $q^*$ be
optimal.` into `Let $r^_$ and $q^_$ be optimal.` and likewise corrupt subscripted
optimality notation. Its release note only fixes table parsing performance. The
candidate keeps 3.9.8 and the content assertions; successful CLI execution is not
content preservation. [Release](https://github.com/prettier/prettier/releases/tag/3.9.10).

[FastAPI release notes](https://github.com/fastapi/fastapi/blob/0.162.0/docs/en/docs/release-notes.md)
cover the entire selected upgrade. Removed `openapi_prefix`/unused constructor
extras, deprecated constructor `root_path`, form/file defaults and parameter-model
changes do not match this application's constructor or JSON-body/individual-query
callers. Native telemetry exporter auto-configuration became opt-in in 0.143.
The fixture now explicitly requests it through `FASTAPI_OTEL_AUTO_CONFIGURE=true`
in its environment case. The owned application must remain inert even with that
setting. Positive controls still require real traces, metrics and logs at all
three loopback OTLP endpoints, while disabled controls require zero provider
calls, registrations, exports and shutdowns. The private cleanup adapter keeps
an exact selected-version guard; review found only a docstring change in upstream
`_runtime.py`, with unchanged executable cleanup. No runtime application source
or public DTO is changed by this cohort.

[Pydantic 2.14.1](https://github.com/pydantic/pydantic/releases/tag/v2.14.1)
fixes allocation/TypedDict/Decimal/timedelta cases; existing public model,
validation, OpenAPI, contact, project and CV contracts are the application oracles.
[Alembic 1.20.1](https://github.com/sqlalchemy/alembic/releases/tag/rel_1_20_1)
requires SQLAlchemy >=2.0, satisfied by selected 2.1.4. Its additional foreign-key
dialect-kwargs autogenerate repair needs SQLAlchemy 2.1.5; these callers do not use
that path. Actual revision-template rendering and driver controls establish a
smaller boundary than live database/autogeneration acceptance.
[HTTPX2 2.16.0](https://github.com/pydantic/httpx2/releases/tag/v2.16.0)
preserves custom cookie policy and defines domain/path ordering. The real
Starlette TestClient controls assert allowed, blocked and unrelated-domain cookies
without network access. [Ruff 0.17.2](https://github.com/astral-sh/ruff/releases/tag/0.17.2)
retains the explicit repository rule set without preview or new ignores.
Python direct proposal targets are maintained MIT distributions except HTTPX2's
BSD-3-Clause; selected HTTPcore2 and Starlette are also BSD-3-Clause. Their
declared Python requirements admit this project's Python 3.12. Fresh normal
resolution selects Starlette 1.10.0, published October 24 and beyond seven days
at review; both old and selected FastAPI admit it through `starlette>=0.46.0`.

[Next 16.4.3](https://github.com/vercel/next.js/releases/tag/v16.4.3) and its MIT
config/plugin packages admit managed Node 24.19.0 and the retained ESLint/TypeScript
peers. React/DOM 19.3.1 satisfy each other and Next's published peers; the published
19.3 declaration packages stay coordinated. The security override and advisory minimum remain 16.4.1; selected direct and optional compiler versions are separately coupled. The machine contract records new Next
manifest/compiler hashes from integrity-verified published tarballs. Native SWC,
Sharp SVG/rsvg, lint/type/build and owned loopback-server controls verify the actual
installed combination. Sharp's exact Next/types/React parent tuple is updated;
its 0.35.5 native assets and rsvg minimum are unchanged.

The #271 lock includes unrelated transitive churn, including napi-postinstall
0.3.7. Review of both integrity-verified helper distributions found new project
`.npmrc` copying (0600), npm configuration/registry lookup and npm subprocess/fallback
behavior in 0.3.7. Existing unrs-resolver 1.12.2 explicitly permits `^0.3.4`.
Normal lock reuse retains reviewed 0.3.4 without an override or ignore. The exact
reviewed manifests, loader/support hashes and denied unrs-resolver lifecycle policy
stay unchanged; its installed native binding and all dependent gates remain
required. An original head's ancestry does not imply acceptance of incidental
lockfile changes superseded by the coherent normal resolution.

## Updater and security evidence boundaries

The fresh inventory contained ten open proposals, two open owner issues and
23 branches. Dependabot's own supersession comments establish the #253/#254
closure dispositions. Recent successful full npm run
[41246040908](https://github.com/googa27/main_website/actions/runs/41246040908) and pip run
[41246040936](https://github.com/googa27/main_website/actions/runs/41246040936)
use `dependencies: null`, `updating-a-pull-request: false`, version-update mode and
the seven-day cooldown; npm resolves the root pnpm workspace and the configured
groups/major holds. This is real full-resolution recovery evidence, beyond the
package-specific #260/#261 recreation runs. Neither the `dynamic` event label nor
the job definitions identify a weekly scheduled trigger. Sunday timing alone is
inference, so that acceptance criterion remains unproved. Historical issue
comments are not fresh Project-board receipts. Issue/Project closure is separate.

Retain full unsuppressed scans: the previously reviewed three minimatch instances
(3.1.5, 10.2.5, 10.2.6) are a caller/default-options reachability disposition,
not patched-version or raw-zero evidence. No global incompatible major override
or advisory suppression is added. Certifi stays selected at 2026.10.23 with its
independent 2026.10.18 security minimum. Official bundle exclusion of the affected
G3 CA does not remove independently preloaded interpreter/system trust; this
container already exposes that CA before loading certifi. No live provider,
production deployment, external TLS or scientific acceptance follows from local
public-synthetic checks.

## Candidate verification

The complete source API suite passes 143 tests; architecture passes
351 tests and 4 subtests. Normal/PDF/DEV normally installed wheel graphs contain
51/53/79 distributions, respectively. Exact published-package coverage audits
check 50/52/78 pins with no skips or findings; the first-party wheel is verified
separately. Development contains the actual SDK-required 0.66b1 instrumentation
components; the normal stable-only profile gate is unchanged. Requirements-file
audits also pass for bootstrap, auditor, architecture and normal/dev/PDF inputs.
Full unsuppressed OSV and pnpm audits retain the same three minimatch instances;
no raw-zero or complete native-hosted acceptance is claimed from local evidence.

The failed pre-fix telemetry positive control, initial lock-only pending-build
gate, namespace-relative process check, cold MCP compilation timeout, strict
Turbo font-fetch failure and the initial new Turbo-control CLI-option conflict
are retained in the task evidence alongside corrected reruns. Existing source
application modules remain byte-identical to the starting main. The final
production build uses the declared root command, strict mode and actual assets.
