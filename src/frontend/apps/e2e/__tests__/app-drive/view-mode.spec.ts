import test, { expect } from "@playwright/test";
import { clearDb, login } from "./utils-common";
import { clickToMyFiles } from "./utils-navigate";
import { createFolderInCurrentFolder } from "./utils-item";
import { expectExplorerBreadcrumbs } from "./utils-explorer";
import { expectRowItem } from "./utils-embedded-grid";

test("Switch the explorer to the grid view and keep it after a reload", async ({
  page,
}) => {
  await clearDb();
  await login(page, "drive@example.com");
  await page.goto("/");
  await clickToMyFiles(page);
  await createFolderInCurrentFolder(page, "testFolder");

  await page.getByRole("button", { name: "Grid view" }).click();
  await expect(page.getByRole("button", { name: "Grid view" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  const card = page
    .locator(".explorer__grid__card")
    .filter({ hasText: "testFolder" });
  await expect(card).toBeVisible();
  await expect(page.getByRole("row", { name: "testFolder" })).toHaveCount(0);

  await page.reload();
  await expect(card).toBeVisible();

  await card.dblclick();
  await expectExplorerBreadcrumbs(page, ["My files", "testFolder"]);

  await page.getByRole("button", { name: "List view" }).click();
  await clickToMyFiles(page);
  await expectRowItem(page, "testFolder");
});
