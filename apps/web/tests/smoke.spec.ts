import { test, expect } from "@playwright/test";
test("home and create trip shell", async ({ page }) => {
  const trips: {
    id: string;
    title: string;
    status: string;
    start_date: string | null;
    end_date: string | null;
  }[] = [];
  await page.route("**/api/v1/trips", async (route) => {
    if (route.request().method() === "POST") {
      const trip = {
        ...route.request().postDataJSON(),
        id: "test-trip",
        status: "IDEA",
      };
      trips.push(trip);
      await route.fulfill({
        status: 201,
        json: { data: trip, meta: {}, error: null },
      });
    } else {
      await route.fulfill({ json: { data: trips, meta: {}, error: null } });
    }
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "凡我所至，皆有所记。" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "我的旅行", exact: true }).click();
  await expect(
    page.getByText("还没有旅行。记下一次出发，或补录一段回忆。"),
  ).toBeVisible();
  await page.getByRole("button", { name: "新建旅行" }).click();
  await page.getByLabel("旅行名称").fill("秋日京都");
  await page.getByRole("button", { name: "保存旅行" }).click();
  await expect(page.getByRole("heading", { name: "秋日京都" })).toBeVisible();
});
