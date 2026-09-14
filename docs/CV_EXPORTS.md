# Public CV exports and curated project fallback

Tracking: [#116](https://github.com/googa27/main_website/issues/116). The current typed `CVProfile` remains the API export source; the current static React-folio adapter remains the website source. No third résumé fixture or raw import path is introduced.

## Maintained libraries and source decisions

| Capability              | Selected boundary                                                                        | Alternatives and reason                                                                                                                                                             |
| ----------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Typed projection        | Existing Pydantic 2.11.7 models, separate immutable export models and a named projection | Domain mapping owns evidence and date precision; general converters cannot infer those policies.                                                                                    |
| JSON Resume conformance | jsonschema 4.26.0 and the exact MIT-licensed @jsonresume/schema 1.3.1 resource           | The canonical package lives in `jsonresume/jsonresume.org/packages/schema`. Validation is offline with the packaged schema, without remote schema resolution.                       |
| Optional PDF            | ReportLab 5.0.1, BSD, with its packaged Vera font                                        | fpdf2 2.8.8 is maintained but LGPL; browser/WeasyPrint engines add dependencies unnecessary for this text document. All supplied text is escaped before ReportLab paragraph markup. |
| PDF verification        | pypdf 6.18.1, BSD-3-Clause, development only                                             | Independently parses actual document bytes, extracted Unicode text, page content and annotations. It is not a runtime renderer.                                                     |
| Project fallback        | Pure projection of current curated CV projects and explicit editorial ordering           | Reject the prototype's GitHub sync, database writes and network retries during GET. Existing explicit sync remains separate.                                                        |

Primary sources checked 2026-09-11: [JSON Resume repository structure](https://jsonresume.org/docs/002-repository-structure), [canonical schema package](https://registry.npmjs.org/@jsonresume/schema/1.3.1), [ReportLab releases](https://docs.reportlab.com/reportlab/changes/), [paragraph markup](https://docs.reportlab.com/reportlab/userguide/ch6_paragraphs/), [ReportLab distribution](https://pypi.org/project/reportlab/5.0.1/), [jsonschema](https://pypi.org/project/jsonschema/4.26.0/), [pypdf](https://pypi.org/project/pypdf/6.18.1/), [fpdf2](https://pypi.org/project/fpdf2/2.8.8/).

The schema and its MIT license are packaged byte-for-byte from the official npm archive. The architecture contract pins the schema SHA-256; the upstream archive SHA-256 is `1d3ab18bc81ca9ccd7abce46e1ef80ac1afad49f48e1d711412bb4775a3e402d`. The export is a supported typed subset, not a general JSON Resume input parser. Free-text location and the evidence/date metadata use extensions allowed by the published schema; consumers may ignore these extensions. No street, city or country code is inferred from free text.

## Public API and installed commands

From a Python 3.12 virtual environment, install the API from the repository root:

```sh
python -m pip install ./apps/api
portfolio-cv --capabilities
portfolio-cv --format jsonresume --output ./resume.json
```

PDF is an explicit optional installation:

```sh
python -m pip install './apps/api[pdf]'
portfolio-cv --format pdf --output ./resume.pdf
```

Use a real existing destination directory. Output is rendered and validated before opening a temporary file in that directory, then replaced atomically. A failed render or replacement preserves the previous artifact. Without `--output`, JSON Resume is written to standard output; PDF requires an explicit path. `python -m app.services.cv.export` exposes the same CLI. These commands load the installed public fixture independently of the caller's working directory. They never acquire provider data.

`--capabilities` reports schema version, input source and whether the optional PDF dependency is installed. Import availability alone does not prove successful rendering; the actual PDF command and installed artifact tests provide that evidence. Missing PDF support returns exit code 2 with a bounded diagnostic. The immutable public Python projection is `app.services.cv.resume.project_resume(profile, options)`; `resume_json(resume)` serializes the published aliases. `app.services.cv.CVService.get_public_resume()` and `render_public_pdf()` are asynchronous orchestration methods. CPU/render work runs in a worker thread.

### Concurrent PDF requests

[Issue #147](https://github.com/googa27/main_website/issues/147) records an actual
ReportLab 5.0.1 concurrent-subsetting failure. The registered TrueType font has
per-document subset assignments, but its shared face parser moves a mutable read
cursor during final font subsetting. The exact 5.0.1 source distribution's
`testParallelConstruction` interleaves documents sequentially; it is not a
simultaneous-thread rendering guarantee. See the [maintained release artifact](https://pypi.org/project/reportlab/5.0.1/)
and [font API guidance](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/).

The existing PDF owner therefore serializes the entire render operation within
one process, from optional imports and font registration through paragraph work
and final document build. Context-managed locking releases on failure. Both active
rendering and waiting for this lock stay inside the existing worker-thread path;
other event-loop work remains responsive. The tradeoff is one PDF render at a time
per application process; this is not a cross-process queue or a throughput gain.
Independent application processes retain their own font state. No per-request font
registry entries, host fonts, network assets or ReportLab internal patches are added.

Real PDF regressions retain the original concurrent text-isolation check and add a
controlled shared-face seek/subsetting overlap, exact document-byte and Unicode
markers, exception recovery from another thread, and event-loop progress during
real rendering contention. The lock does not change text, layout, public
signatures, optional installation or CLI atomic replacement semantics.

| HTTP route                                     | Response                                                                           |
| ---------------------------------------------- | ---------------------------------------------------------------------------------- |
| `GET /api/cv/resume`                           | Typed JSON Resume document                                                         |
| `GET /api/cv/resume/download`                  | Same document as a UTF-8 JSON attachment                                           |
| `GET /api/cv/pdf`                              | Actual `application/pdf` attachment; 503 when the optional renderer is absent      |
| `GET /api/cv/download?format=pdf`              | Same binary PDF route for existing download callers                                |
| `POST /api/cv/export` with `format=jsonresume` | Existing export envelope containing JSON Resume text                               |
| Existing PDF export envelope                   | Same-origin `download_path` when available; explicit unavailable content otherwise |

Existing JSON/MDX envelopes remain available. JSON Resume and PDF retain projects, awards and their evidence limitations. Career/certificate dates are emitted at month precision, education at year precision; original date-precision notes and profile revision timestamps are retained. This avoids presenting placeholder day 01 as a verified exact date. No publication, deployment or model calibration is inferred from a project entry. The public CV contains its reviewed contact fields; the separate chatbot context continues to omit phone, email and profile-picture data.

The `/cv/preview` frontend route composes the current static About content. It builds without an API or network fetch. Optional download links require an explicitly configured `NEXT_PUBLIC_API_BASE_URL` with HTTP(S), no credentials, query or fragment; the configured API must expose these routes and, for PDF, install the extra. This static preview is not claimed to be a pixel-identical PDF preview or an automatically synchronized API snapshot.

## Curated project reads

`GET /api/projects` reads the database and falls back to current curated CV projects when the database is empty or its read raises `SQLAlchemyError`. No acquisition or writes are performed by this route. A nonempty database with an out-of-range page returns an empty page with the database's full count, not unrelated fallback records.

Curated ordering is featured first, then explicit nonnegative `display_priority` (zero is meaningful), then stable source order. The full snapshot is ordered before pagination. `skip >= 0` and `1 <= limit <= 100` are validated at HTTP and pure-projection boundaries. URL-derived negative 48-bit display identities are stable and safe as JavaScript integers; duplicate identities are rejected. They are not GitHub IDs and do not imply database detail/score endpoints exist for curated records.

Fallback collections report `source=curated_cv`, `metrics_available=false` and `timestamp_kind=profile_last_updated`. Existing numeric fields use compatibility zeros, not observed provider counts. Database collections retain their provider metadata and existing score heuristic within each page, with globally featured-first selection and full collection totals. This does not repair the separately documented frontend project-client schema mismatch.

## Preserved draft disposition and extension boundaries

The local prototype commits `53ff883` and `70063ee` mixed useful behavior with private raw history. Their original refs/files remain preserved. This change reimplements the useful typed export, optional PDF, static preview and curated project ordering against the current public source. It does not import that history, duplicate résumé JSON, add private query toggles, infer hidden grouping metadata, copy old databases or perform acquisition during reads. No default time cutoff silently removes older roles.

PDP acquisition, FPF mathematical formulation and ui_and_artifacts governed report contracts are not required for rendering one repository's already curated CV. General numerical/report products continue to cross their public contracts; no internal cross-repository imports or new MCP server is introduced.

Fitness tests pin the offline schema/license and package resources, forbid acquisition/database imports in projection modules, preserve optional PDF ownership and require the static preview to reuse current content. API tests cover actual PDF bytes and escaped markup, concurrency, HTTP attachments, optional absence, atomic failure preservation, date/evidence semantics and database read-only fallback. `scripts/check_installed_api.py` exercises the runtime wheel and CLI from an isolated interpreter outside the source tree. Visual inspection additionally checks the generated public PDF's page breaks and glyphs. These are synthetic/local artifact checks, not live provider or deployed-browser acceptance.

The isolated build also exposed [#117](https://github.com/googa27/main_website/issues/117), the deprecated API license-table syntax. The existing MIT expression now uses modern SPDX metadata with Setuptools >=77.0.3, following the [PyPA packaging guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license). This is a syntax migration, not a new root license claim. Wheel metadata and a warning-free build verify the actual result.

The PDF extra explicitly pins Pillow 12.3.0, the version already used by the verified renderer environment. ReportLab's broader `Pillow>=9` requirement alone permits vulnerable historical versions: the actual PR OSV run identified 9.5.0 and prompted [#120](https://github.com/googa27/main_website/issues/120). The [upstream 12.3.0 security release](https://pillow.readthedocs.io/en/stable/releasenotes/12.3.0.html) addresses the reported parser, memory and font issues. Both distribution and requirements profiles enforce the same constraint, independently of the text-only renderer's asset refusal. An actual resolver must reject the old version; selecting a current version in one test environment alone does not enforce the supported dependency boundary.

Stored project identities and explicit detail routes are documented in [Project read identities](PROJECT_API.md). Curated display IDs carry no stored or provider identity.
