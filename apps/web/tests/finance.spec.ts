import { expect, test } from "@playwright/test";
import { apiPath, apiPattern, currentUser, oidcTestEnabled } from "./api-route";
import type { Booking, Expense } from "../src/lib/types";

test.use({ timezoneId: "Asia/Hong_Kong" });

test("OIDC BFF exposes finance routes and rejects client identity and unlisted queries", async ({
  request,
}) => {
  test.skip(!oidcTestEnabled, "Requires the optional OIDC Web mode");
  const id = "00000000-0000-4000-8000-000000000004";
  for (const path of [
    "bookings?limit=1&offset=0",
    "expenses?limit=1",
    `trips/${id}/bookings`,
    `trips/${id}/expenses`,
    `trips/${id}/summary`,
    `trips/${id}/expenses/summary`,
  ]) {
    const response = await request.get(`/api/bff/${path}`);
    expect([401, 503]).toContain(response.status());
  }
  const identity = await request.post("/api/bff/expenses", {
    data: { user_id: id },
  });
  expect(identity.status()).toBe(400);
  expect((await identity.json()).error.code).toBe("IDENTITY_INPUT_REJECTED");
  const query = await request.delete(
    `/api/bff/expenses/${id}?version=1&unknown=true`,
  );
  expect(query.status()).toBe(400);
  expect((await query.json()).error.code).toBe("QUERY_REJECTED");
});

test("records return transport, accommodation and exact multicurrency expenses, edits and deletes", async ({
  page,
}) => {
  const trip = {
    id: "trip-finance",
    title: "京都往返",
    status: "PLANNING",
    start_date: "2026-10-01",
    end_date: "2026-10-05",
    timezone: "Asia/Tokyo",
    summary: null,
  };
  const bookings: Booking[] = [];
  const expenses: Expense[] = [];
  let conflict = false;
  let summaryReads = 0;
  await page.route(apiPattern, async (route) => {
    const request = route.request();
    const path = apiPath(request.url());
    const method = request.method();
    let data: unknown = [];
    if (path === "/me") data = currentUser;
    else if (path === "/trips") data = [trip];
    else if (path === `/trips/${trip.id}`) data = trip;
    else if (path.endsWith("/summary")) {
      summaryReads += 1;
      data = {
        booking_count: bookings.length,
        expense_count: expenses.length,
        original_totals: expenses.length
          ? [{ currency: "JPY", amount: "1200.1234" }]
          : [],
        paid_totals: expenses.length
          ? [{ currency: "CNY", amount: "60.4321" }]
          : [],
        categories: expenses.length
          ? [{ category: "餐饮", currency: "CNY", amount: "60.4321" }]
          : [],
      };
    } else if (path.endsWith("/bookings") && method === "GET") data = bookings;
    else if (path.endsWith("/expenses") && method === "GET") data = expenses;
    else if (path === "/bookings" && method === "POST") {
      const body = request.postDataJSON();
      expect(typeof body.amount).toBe("string");
      const row = {
        ...body,
        id: `booking-${bookings.length}`,
        version: 1,
      } as Booking;
      if (bookings.length === 0) {
        row.start_at = "2026-10-01T10:00:22.123456+09:00";
        row.end_at = "2026-10-01T09:30:22.123456+08:00";
      }
      bookings.push(row);
      data = row;
    } else if (path === "/expenses" && method === "POST") {
      const body = request.postDataJSON();
      expect(body.original_amount).toBe("1200.1234");
      expect(body.settled_amount).toBe("60.4321");
      expect(body.exchange_rate).toBe("0.05035492");
      expect(body.occurred_at).toBe("2026-10-02T02:00:00.000Z");
      const row = { ...body, id: "expense-1", version: 1 } as Expense;
      expenses.push(row);
      data = row;
    } else if (path.startsWith("/bookings/") && method === "PATCH") {
      const body = request.postDataJSON();
      expect(body.version).toBe(1);
      expect(body.start_at).toBe("2026-10-01T10:00:22.123456+09:00");
      expect(body.end_at).toBe("2026-10-01T09:30:22.123456+08:00");
      const row = bookings.find((b) => path.endsWith(b.id))!;
      Object.assign(row, body, { version: 2 });
      data = row;
    } else if (path.startsWith("/expenses/") && method === "PATCH") {
      if (conflict) {
        await route.fulfill({
          status: 409,
          json: {
            data: null,
            meta: {},
            error: { code: "VERSION_CONFLICT", message: "reload" },
          },
        });
        return;
      }
      const body = request.postDataJSON();
      Object.assign(expenses[0], body, { version: 2 });
      data = expenses[0];
    } else if (path.startsWith("/bookings/") && method === "DELETE") {
      expect(new URL(request.url()).searchParams.get("version")).toBe("2");
      bookings.splice(
        bookings.findIndex((b) => path.endsWith(b.id)),
        1,
      );
      data = null;
    } else if (path.startsWith("/expenses/") && method === "DELETE") {
      expenses.splice(0, 1);
      data = null;
    }
    await route.fulfill({ json: { data, meta: {}, error: null } });
  });
  await page.goto(`/trips/${trip.id}`);
  await page.getByRole("button", { name: "管理预订与费用" }).click();
  for (const [type, title] of [
    ["FLIGHT", "去程机票"],
    ["TRAIN", "返程车票"],
    ["HOTEL", "京都住宿"],
  ]) {
    await page.getByRole("button", { name: "添加预订", exact: true }).click();
    const form = page.getByRole("form", { name: "预订表单" });
    await form.getByLabel("预订名称").fill(title);
    await form.getByLabel("预订类型").selectOption(type);
    await form.getByLabel("确认号").fill("TOVIA123");
    await form.getByLabel("开始时间（设备时区）").fill("2026-10-01T09:00");
    await form.getByLabel("结束时间（设备时区）").fill("2026-10-02T09:00");
    await form.getByLabel("预订价格（选填）").fill("100.1234");
    await form.getByLabel("预订币种（选填）").fill("CNY");
    await form.getByRole("button", { name: "保存预订" }).click();
    await expect(form).toHaveCount(0);
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible();
  }
  await expect(page.getByText("3 项预订 · 0 笔费用")).toBeVisible();
  await page.getByRole("button", { name: "编辑预订" }).first().click();
  await page
    .getByRole("form", { name: "预订表单" })
    .getByLabel("备注", { exact: true })
    .fill("座位已确认");
  await page.getByRole("button", { name: "保存预订" }).click();
  await expect(page.getByText("座位已确认")).toBeVisible();
  await page.getByRole("button", { name: "费用", exact: true }).click();
  await page.getByRole("button", { name: "添加费用", exact: true }).click();
  const form = page.getByRole("form", { name: "费用表单" });
  await form.getByLabel("商户", { exact: true }).fill("京都餐馆");
  await form.getByLabel("费用类别").fill("餐饮");
  await form.getByLabel("原币金额").fill("1200.1234");
  await form.getByLabel("原币币种").fill("JPY");
  await form.getByLabel("结算金额（选填）").fill("60.4321");
  await form.getByLabel("结算币种（选填）").fill("CNY");
  await form.getByLabel("实际汇率（结算币 / 原币，选填）").fill("0.05035492");
  await form.getByLabel("消费时间（设备时区）").fill("2026-10-02T10:00");
  await form.getByLabel("支付方式").fill("信用卡");
  await form.getByRole("button", { name: "保存费用" }).click();
  await expect(page.getByText("实际花费：CNY 60.4321")).toBeVisible();
  await page.getByRole("button", { name: "编辑费用" }).click();
  await page
    .getByRole("form", { name: "费用表单" })
    .getByLabel("备注", { exact: true })
    .fill("保留未提交输入");
  conflict = true;
  await page.getByRole("button", { name: "保存费用" }).click();
  await expect(
    page.getByRole("form", { name: "费用表单" }).getByRole("alert"),
  ).toContainText("记录已被更新");
  await expect(
    page
      .getByRole("form", { name: "费用表单" })
      .getByLabel("备注", { exact: true }),
  ).toHaveValue("保留未提交输入");
  await page
    .getByRole("form", { name: "费用表单" })
    .getByRole("button", { name: "取消", exact: true })
    .click();
  page.on("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "删除费用" }).click();
  await expect(page.getByText("3 项预订 · 0 笔费用")).toBeVisible();
  await page.getByRole("button", { name: "预订", exact: true }).click();
  await page.getByRole("button", { name: "删除预订" }).first().click();
  await expect(page.getByText("2 项预订 · 0 笔费用")).toBeVisible();
  expect(summaryReads).toBeGreaterThan(5);
});

test("independent records remain reachable on a narrow screen and have recoverable errors", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let fail = true;
  await page.route(apiPattern, async (route) => {
    const path = apiPath(route.request().url());
    if (path === "/bookings" && fail) {
      await route.fulfill({
        status: 503,
        json: {
          data: null,
          meta: {},
          error: { code: "DATABASE_UNAVAILABLE", message: "unavailable" },
        },
      });
      return;
    }
    await route.fulfill({
      json: { data: path === "/me" ? currentUser : [], meta: {}, error: null },
    });
  });
  await page.goto("/trips/records");
  await expect(
    page.getByRole("heading", { name: "全部预订与费用" }),
  ).toBeVisible();
  await expect(page.getByText("数据库暂时无法连接")).toBeVisible();
  fail = false;
  await page.getByRole("button", { name: "重试" }).click();
  await expect(
    page.getByText("这一页暂无预订", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "添加预订", exact: true }).click();
  await expect(page.getByLabel("所属旅行")).toHaveValue("");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../tmp/v04-finance-mobile.png",
    fullPage: true,
  });
});
