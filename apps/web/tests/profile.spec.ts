import { expect, test } from "@playwright/test";
import { apiPath, apiPattern, currentUser } from "./api-route";

test("edits profile details and downloads the complete JSON export", async ({
  page,
}) => {
  const savedUser = { ...currentUser };
  await page.route(apiPattern, async (route) => {
    const request = route.request();
    const path = apiPath(request.url());
    if (path === "/me" && request.method() === "GET") {
      await route.fulfill({ json: { data: savedUser, meta: {}, error: null } });
      return;
    }
    if (path === "/me" && request.method() === "PATCH") {
      Object.assign(savedUser, request.postDataJSON());
      await route.fulfill({ json: { data: savedUser, meta: {}, error: null } });
      return;
    }
    if (path === "/me/export") {
      await route.fulfill({
        json: {
          data: {
            schema_version: "1.0",
            exported_at: "2026-09-22T00:00:00Z",
            data: {
              user: savedUser,
              trips: [],
              trip_days: [],
              visits: [],
              activities: [],
              places: [],
              wishlist_items: [],
            },
          },
          meta: {},
          error: null,
        },
      });
      return;
    }
    throw new Error(
      `Unexpected profile API request: ${request.method()} ${path}`,
    );
  });

  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "我的账户" })).toBeVisible();
  await page.getByLabel("显示名称").fill("旅行记录者");
  await page.getByRole("button", { name: "保存资料" }).click();
  await expect(page.getByText("资料已保存。")).toBeVisible();
  expect(savedUser.display_name).toBe("旅行记录者");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载我的数据" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^tovia-export-.*\.json$/);
});

test("hides the inbox entry until its data workflow exists", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page
      .getByRole("navigation", { name: "主导航" })
      .getByRole("link", { name: "收件箱" }),
  ).toHaveCount(0);
  const response = await page.goto("/inbox");
  expect(response?.status()).toBe(404);
});
