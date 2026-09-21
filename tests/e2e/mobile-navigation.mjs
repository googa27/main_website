import assert from "node:assert/strict";

// Supply a real Playwright Page against the built static site; no DOM mocks.
export async function checkMobileNavigation(page, baseUrl) {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(new URL("/", baseUrl).href);
  const navigation = page.getByRole("navigation", { name: "Main" });
  const button = navigation.getByRole("button", { name: "Navigation menu" });
  await button.waitFor({ state: "visible" });
  assert.equal(await button.getAttribute("aria-expanded"), "false");
  const controls = await button.getAttribute("aria-controls");
  assert.ok(controls, "the disclosure must identify its controlled panel");
  const panel = page.locator(`[id="${controls}"]`);
  assert.equal(await panel.count(), 1);
  assert.equal(await panel.isVisible(), false);

  await button.focus();
  await page.keyboard.press("Enter");
  await panel.waitFor({ state: "visible" });
  assert.equal(await button.getAttribute("aria-expanded"), "true");
  const links = panel.getByRole("link");
  assert.deepEqual(await links.allTextContents(), [
    "Home",
    "About",
    "Projects",
    "Contact",
  ]);
  assert.deepEqual(
    await links.evaluateAll((elements) =>
      elements.map((element) => element.getAttribute("href")),
    ),
    ["/", "/about", "/projects", "/contact"],
  );

  await page.keyboard.press("Tab");
  assert.equal(
    await links
      .first()
      .evaluate((element) => element === document.activeElement),
    true,
  );
  await page.keyboard.press("Escape");
  await panel.waitFor({ state: "hidden" });
  assert.equal(await button.getAttribute("aria-expanded"), "false");
  assert.equal(
    await button.evaluate((element) => element === document.activeElement),
    true,
  );

  await page.keyboard.press("Space");
  await panel.waitFor({ state: "visible" });
  await panel.getByRole("link", { name: "About", exact: true }).click();
  await page.waitForURL((url) => /^\/about\/?$/.test(url.pathname));
  await panel.waitFor({ state: "hidden" });
  assert.equal(await button.getAttribute("aria-expanded"), "false");

  await button.click();
  await panel.waitFor({ state: "visible" });
  assert.equal(
    await panel
      .getByRole("link", { name: "About", exact: true })
      .getAttribute("aria-current"),
    "page",
  );
  await button.focus();
  // Tab through the four links and out of the navigation, without a focus trap.
  for (let index = 0; index < 5; index += 1) {
    await page.keyboard.press("Tab");
  }
  await panel.waitFor({ state: "hidden" });
  assert.equal(await button.getAttribute("aria-expanded"), "false");
  assert.equal(
    await navigation.evaluate((element) =>
      element.contains(document.activeElement),
    ),
    false,
  );

  await page.setViewportSize({ width: 1440, height: 1000 });
  await button.waitFor({ state: "hidden" });
  for (const name of ["Home", "About", "Projects", "Contact"]) {
    assert.equal(
      await navigation.getByRole("link", { name, exact: true }).isVisible(),
      true,
    );
  }
}
