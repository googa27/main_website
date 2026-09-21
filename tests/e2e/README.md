# End-to-end checks

`mobile-navigation.mjs` exports `checkMobileNavigation(page, baseUrl)`. It uses a
real Playwright Page and Node's built-in assertions to check the mobile disclosure,
Enter/Space activation, ordinary Tab order, Escape/focus restoration, link
navigation/dismissal, focus-out dismissal, current-page semantics and desktop
link visibility. It neither starts a server nor owns a browser. No DOM mocks or
frontend test framework are introduced.

Serve the built `apps/web/out` on a loopback address. In an existing, explicitly
versioned Playwright environment, supply a fresh browser/context/Page and call:

```js
const { checkMobileNavigation } = await import(
  "/absolute/repository/tests/e2e/mobile-navigation.mjs"
);
await checkMobileNavigation(page, "http://127.0.0.1:PORT");
```

The caller owns browser/server cleanup, network policy and raw receipts. Use a
bounded timeout, record source and browser identities, disallow unrelated
external requests, and close resources even when an assertion fails. An
assertion failure must remain a failure, never an ignored diagnostic.

For issue159, run the same assertion against the original built baseline to
record the missing accessible disclosure, then the corrected build. Inspect
collapsed/expanded mobile screenshots and desktop layout in light/dark preference
separately; this interaction check does not certify visual quality or screen-reader
support. Check the layout at390px and1440px plus the md breakpoint (767/768px).

The maintained `pnpm test` frontend command still reports `No tests yet`; it does
not run this check. Browser execution requires an already provisioned browser
fixture and remains explicit, not a fabricated CI claim. Browser-to-API tests
remain deferred until a deployment-like web/API fixture is maintained.
