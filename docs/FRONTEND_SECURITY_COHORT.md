# Current frontend security cohort

Issue [#263](https://github.com/googa27/main_website/issues/263) owns this
2026-10-31 review. It extends the historical security repairs without rewriting
their evidence. The canonical current selections and consumer fingerprints are
in `architecture.frontend_security_cohort` and `next_security_policy` in
`docs/ARCHITECTURE.yaml`.

Next and its lint configuration move together to **16.4.1**, including the exact
same-version environment, ESLint plugin and optional native compiler assets.
Zod moves to **4.6.6** through a bounded, compatible 4.x override. Both existing
package identities are MIT licensed; registry publication dates are October 14
and October 11 respectively, outside the seven-day update cooldown. Node
24.19.0, pnpm 10.34.5, strict peers, React 19.3.0 and the reviewed TypeScript
ESLint 8.72.0 umbrella remain selected. Original Next PR #259 and config PR #262
are retained in the integration ancestry; their 16.4.0 targets alone do not
repair the current Next advisories.

## Application boundary and executable controls

The three newer Next advisories are
[image optimization](https://github.com/advisories/GHSA-2464-fhr4-w9xw),
[typed-array cache results](https://github.com/advisories/GHSA-673q-mjm6-r5xr), and
[Server Actions](https://github.com/advisories/GHSA-p3m5-59mp-jv5r). Current source
uses static export and unoptimized images, exposes no Server Actions, and has no
`use cache` functions. The image-library workaround Sharp 0.35.5 was already
selected. These source facts bound reachability; they do not prove a deployed
configuration. The package floor is upgraded regardless. Existing real compiler,
developer-origin, process-ownership and Sharp consumer controls remain required.
The GNU compiler and Next manifest hashes come from independently downloaded
registry tarballs verified against their published SHA-512 integrity.

[Zod's maintained repair](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)
checks an existing array/set/map upper bound before validating collection
elements. It does not cap errors for arbitrary unconstrained arrays. The actual
consumer is `eslint-plugin-react-hooks`, resolved through `eslint-config-next`;
the application has no Zod import. The required runtime controls resolve that
same consumer and assert zero element callbacks for oversized constrained
collections, one bound error, and successful ordinary values.

## Explicit minimatch disposition

The unsuppressed audit still reports minimatch **3.1.5, 10.2.5 and 10.2.6** under
[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).
These are affected package instances within the advisory's broad `<11.0.1`
range. They are not reported as patched packages or as three independently
demonstrated application exploits.

The advisory describes growth in `firstPhasePreProcess()` followed by pairwise
processing, enabled by `optimizationLevel >= 2`. The exact 3.1.5 implementation
has neither that option nor those preprocessing phases. Modern 10.x defaults to
level 1. Review of every locked 10.x parent found these options:

| Parent                      | Resolved minimatch | Caller options                             |
| --------------------------- | ------------------ | ------------------------------------------ |
| ESLint 10.10.0              | 10.2.5             | `dot: true`                                |
| @eslint/config-array 0.23.5 | 10.2.6             | `dot: true`, optionally `flipNegate: true` |
| TypeScript ESTree 8.72.0    | 10.2.6             | `dot: true` for project-service patterns   |

The required gate fingerprints these installed caller files and exercises the
actual resolved minimatch versions with ordinary globs and a bounded advisory
pattern. Default and caller options retain one pattern; an explicit level-2
positive control on both 10.x packages expands it, demonstrating that the option
boundary is meaningful without a timing assertion. Existing brace-expansion
controls continue to cover CommonJS and ES-module exports separately.

No parent accepts minimatch 11. Forcing it would violate 3.x and 10.x ranges and
break concrete 3.x consumers that call the CommonJS export as a function.
Version 11.0.1 was published October 27, inside this review's seven-day cooldown;
no cooldown exception, global audit suppression or major override is introduced.
This is an evidence-backed disposition of the current consumer paths, while
preserving the advisory records. A supported patched parent/backport, revised
advisory mechanism, package/caller drift, level-2 opt-in or new runtime consumer
requires renewed review. Caller-byte drift fails the required gate.

Run `pnpm install --frozen-lockfile`, `pnpm run check:dependency-build-policy`,
`pnpm run lint`, `pnpm run typecheck`, `pnpm run build`, and
`python -m pytest tests/architecture` through the declared managed environment.
`pnpm audit --json` remains unsuppressed; its retained minimatch findings are
expected and must be reported. Native CI and actual resulting-main verification
are separate acceptance evidence. No deployment is authorized by this repair.
