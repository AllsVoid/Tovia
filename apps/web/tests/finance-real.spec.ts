import { expect, test } from "@playwright/test";

const realApi = process.env.TOVIA_REAL_API_URL;
test.use({ timezoneId: "Asia/Hong_Kong" });

test("real API and PostGIS preserve exact expenses when a trip is removed", async ({
  page,
  request,
}) => {
  test.skip(
    !realApi,
    "Opt in with TOVIA_REAL_API_URL and a dedicated development-auth database",
  );
  const base = `${realApi}/api/v1`;
  const response = await request.post(`${base}/trips`, {
    data: {
      title: `0.4 实库验收 ${Date.now()}`,
      timezone: "Asia/Tokyo",
      status: "PLANNING",
    },
  });
  expect(response.status()).toBe(201);
  const trip = (await response.json()).data;
  const records: { kind: "bookings" | "expenses"; id: string }[] = [];
  try {
    await page.goto(`/trips/${trip.id}`);
    await page.getByRole("button", { name: "管理预订与费用" }).click();
    for (const [type, title] of [
      ["FLIGHT", "真实去程机票"],
      ["TRAIN", "真实返程车票"],
      ["HOTEL", "真实京都住宿"],
    ]) {
      await page.getByRole("button", { name: "添加预订", exact: true }).click();
      const form = page.getByRole("form", { name: "预订表单" });
      await form.getByLabel("预订名称").fill(title);
      await form.getByLabel("预订类型").selectOption(type);
      await form.getByLabel("开始时间（设备时区）").fill("2026-10-01T09:00");
      await form.getByLabel("预订价格（选填）").fill("100.1234");
      await form.getByLabel("预订币种（选填）").fill("CNY");
      const saved = page.waitForResponse(
        (r) =>
          r.url() === `${base}/bookings` && r.request().method() === "POST",
      );
      await form.getByRole("button", { name: "保存预订" }).click();
      const result = await saved;
      expect(result.status()).toBe(201);
      records.push({ kind: "bookings", id: (await result.json()).data.id });
      await expect(form).toHaveCount(0);
    }
    await page.getByRole("button", { name: "费用", exact: true }).click();
    for (const amount of ["0.1", "0.2"]) {
      await page.getByRole("button", { name: "添加费用", exact: true }).click();
      const form = page.getByRole("form", { name: "费用表单" });
      await form.getByLabel("商户", { exact: true }).fill("实库餐馆");
      await form.getByLabel("费用类别").fill("餐饮");
      await form.getByLabel("原币金额").fill(amount);
      await form.getByLabel("原币币种").fill("USD");
      await form.getByLabel("消费时间（设备时区）").fill("2026-10-02T10:00");
      const saved = page.waitForResponse(
        (r) =>
          r.url() === `${base}/expenses` && r.request().method() === "POST",
      );
      await form.getByRole("button", { name: "保存费用" }).click();
      const result = await saved;
      expect(result.status()).toBe(201);
      records.push({ kind: "expenses", id: (await result.json()).data.id });
      await expect(form).toHaveCount(0);
    }
    await expect(page.getByText("实际花费：USD 0.3000")).toBeVisible();
    await page.reload();
    await page.getByRole("button", { name: "管理预订与费用" }).click();
    await expect(page.getByText("3 项预订 · 2 笔费用")).toBeVisible();
    await page.screenshot({
      path: "../../tmp/v04-finance-real-desktop.png",
      fullPage: true,
    });
    page.once("dialog", async (dialog) => {
      expect(dialog.message()).toContain("预订和费用会解除");
      await dialog.accept();
    });
    await page.getByRole("button", { name: "删除旅行", exact: true }).click();
    await expect(page).toHaveURL(/\/trips$/);
    await page
      .getByRole("link", { name: "全部预订与费用（含独立记录） →" })
      .click();
    await expect(
      page.getByText("真实去程机票", { exact: false }).first(),
    ).toBeVisible();
    for (const record of records) {
      const retained = (
        await (await request.get(`${base}/${record.kind}/${record.id}`)).json()
      ).data;
      expect(retained.trip_id).toBeNull();
      if (record.kind === "expenses")
        expect(["0.1000", "0.2000"]).toContain(retained.original_amount);
    }
  } finally {
    await request.delete(`${base}/trips/${trip.id}`);
    for (const record of records) {
      const response = await request.get(`${base}/${record.kind}/${record.id}`);
      if (response.ok()) {
        const row = (await response.json()).data;
        await request.delete(
          `${base}/${record.kind}/${record.id}?version=${row.version}`,
        );
      }
    }
  }
});
