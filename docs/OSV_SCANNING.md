# OSV workflow result handling

Issue [#263](https://github.com/googa27/main_website/issues/263) owns the
scanner repair separately from the dependency repairs. Both CI callers use
Google's maintained reusable workflows from release
[v2.7.0](https://github.com/google/osv-scanner-action/releases/tag/v2.7.0),
pinned to commit `b1d267aea5211fa648d9d442fa64b90dbdcbdd36`.

`export-results: false` disables optional JSON **job output strings**. The PR
workflow still scans the target and PR code, compares complete results, and
uploads `old-json-results`, `new-json-results`, and `OSV Scanner SARIF file`
artifacts with the upstream five-day retention. The push workflow still reports
all findings in its SARIF artifact. Both upload SARIF to code scanning and
explicitly retain `fail-on-vuln: true`. There is no local finding filter or
truncation. Upstream completion guards fail a scan that exits unsuccessfully
without producing a nonempty JSON result before invoking the reporter.

The upstream PR workflow persists checkout credentials for its subsequent
checkout operations. This existing upstream behavior is unchanged by the
caller update; local checkouts retain `persist-credentials: false`. The caller
grants only contents/actions read access and security-events write access for
the code-scanning upload. An independent offline Zizmor 1.28.0 audit of the
upstream PR workflow reports this existing `artipacked` warning as medium
severity with low confidence. Keep that upstream warning visible during review;
the repository's caller-only audit does not inspect remote workflow internals.

## Historical failure and measured evidence

At PR258 head `92061ed9334e61a92be51cd44d27981ae8b8781e`, hosted
[job124626088302](https://github.com/googa27/main_website/actions/runs/41231136080/job/124626088302)
scanned all seven manifest sets, ran the reporter, and uploaded SARIF. It then
failed during job output evaluation with `Maximum object size exceeded`.
The pinned v2.3.8 workflow exported both complete JSON files into
`GITHUB_OUTPUT` and promoted them to job/workflow outputs; neither caller uses
those outputs. GitHub documents a
[1 MB job output limit with UTF-16 size accounting](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idoutputs).
Upstream [PR130](https://github.com/google/osv-scanner-action/pull/130) addresses
this precise mechanism by making result exports optional.

The downloaded ZIP digests matched the native artifact digests. Uncompressed
historical file sizes and SHA-256 values are:

| File | UTF-8 bytes | UTF-16 bytes | SHA-256 |
| --- | ---: | ---: | --- |
| old-results.json | 1,634,705 | 3,267,448 | `9b8b16344f99fe874d96fe15361a595bbc4e32cf8a1235dda67d84d6a12bcec1` |
| new-results.json | 1,334,920 | 2,667,878 | `231fdc59808c2170358a3d4877fc2b51ba2e8f2cf2b6cd9664a92ebff64905f2` |
| results.sarif | 1,168 | 2,336 | `f79825c5ba3bd06c4ba64e2bbe20e3e50f5df79bc3b22279160a1258c2e37f32` |

Both JSON values independently exceed the output limit. Their combined
UTF-16 payload is 5,935,326 bytes before template overhead. The stored SARIF
contains zero **PR-difference** results; the complete old/new JSON files still
contain vulnerability records. This historical evidence neither turns that
failed job into a passing check nor establishes a clean full-repository audit.
On that pull-request event the push-only full-scan job was skipped by its
event condition; it is not a dependency of the PR scan.

## Verification and upgrades

Run `python -m pytest tests/architecture/test_osv_workflow_contract.py` and the
repository architecture/policy checks after a caller change. For an upstream
upgrade, dereference the release tag to a commit and inspect both workflows:
the export step must remain gated independently of scanning, reporting and
artifact uploads; `fail-on-vuln` must still reach the reporter; failed scans
without results must fail before reporting.

Replay the exact upstream export and completion-guard shell steps with the
preserved native JSON files. The historical exporter must exceed the documented
output limit, while the configured export-disabled path must emit no result
strings and leave all input/artifact bytes intact. Exercise the actual reporter
with identical old/new results (no introduced findings), an empty old result and
the preserved new result (introduced findings must return nonzero and retain
SARIF), and failed/missing scan controls. These local controls do not replace
the resulting commit's hosted scans and code-scanning inspection.
