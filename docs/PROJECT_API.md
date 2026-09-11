# Project read identities

The optional API distinguishes local database identity from GitHub repository identity. This fixes [issue123](https://github.com/googa27/main_website/issues/123) without changing existing lookup semantics or performing a database migration. The static website remains independent of the API.

| Read operation                            | Identifier meaning                                                                                             | Result                                                        |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `GET /api/projects`                       | Each stored record's `id` is its local database primary key; `github_id` is the nullable GitHub repository ID. | Stable database page or explicitly labelled curated fallback. |
| `GET /api/projects/by-id/{project_id}`    | Local database primary key from the collection.                                                                | The matching stored record, or 404.                           |
| `GET /api/projects/by-github/{github_id}` | GitHub repository ID.                                                                                          | The matching stored record, or 404.                           |
| `GET /api/projects/{project_id}`          | Legacy **GitHub** repository ID, despite the old parameter name.                                               | Existing lookup preserved; operation deprecated in OpenAPI.   |
| `GET /api/projects/{project_id}/score`    | Local database primary key.                                                                                    | Existing scoring read preserved.                              |

The new explicit routes accept positive signed 64-bit identifiers; invalid, zero, negative or out-of-range values fail validation with 422 before a lookup. An absent valid identifier returns 404. They never guess or retry using the other namespace. The legacy route retains its integer parsing behavior and GitHub lookup, including 404 for unknown IDs; existing callers should migrate to the explicitly named GitHub route.

For example, a stored row may have `id=1` and `github_id=987654321`, while another row has `id=2` and `github_id=1`. `/by-id/1` correctly returns the first row; `/by-github/1` and the legacy `/1` return the second. Retrying a failed local lookup as a provider lookup would silently select a different record, so it is deliberately unsupported.

Curated fallback records have stable negative display IDs, `github_id=null`, `source="curated_cv"` and unavailable measured metrics. Those IDs are not database-detail or provider-lookup identifiers. A stored local row may also have `github_id=null`; its positive local-ID route remains available. See [the curated read contract](CV_EXPORTS.md#curated-project-reads).

One typed `_project_response` projection in `app.routers.projects` supplies stored collection and detail responses, including topics, timestamps, featured state and both identities. These reads neither acquire provider data nor commit database changes. Existing explicit sync and featured-acquisition surfaces remain separate and are not reclassified by this change. This API does not establish ownership/authorization or attest current GitHub state.

## Maintained boundary and verification

FastAPI supplies path parsing, ordered route matching, OpenAPI discovery and operation deprecation; Pydantic supplies typed response validation. SQLAlchemy's existing service methods own exact database queries. No new dependency, dispatch framework or namespace-guessing algorithm is needed. Primary references: [FastAPI route order](https://fastapi.tiangolo.com/tutorial/path-params/#order-matters) and [deprecation metadata](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/#deprecate-a-path-operation), checked 2026-09-11.

`python -m pytest tests/test_project_identifiers.py tests/test_project_fallback.py` from `apps/api` exercises actual ASGI requests with synthetic SQLite records: collisions, collection/detail parity, unchanged legacy/score meanings, nullable provider identity, curated scope, bounded invalid-input refusal, no acquisition/writes and OpenAPI discovery. Run the complete API and architecture suites before publication. The machine policy is `architecture.project_read_identity` in `docs/ARCHITECTURE.yaml`.
