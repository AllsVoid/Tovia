import { expect, test } from "@playwright/test";

const enabled = process.env.NEXT_PUBLIC_WEB_AUTH_MODE === "oidc";

test("keeps the existing shell and skips BFF calls when OIDC is disabled", async ({
  page,
}) => {
  test.skip(enabled, "This assertion covers the default disabled mode");
  let requests = 0;
  await page.route("**/api/bff/me", async (route) => {
    requests += 1;
    await route.abort();
  });

  await page.goto("/");
  await expect(page.getByText("所至 · 旅行簿")).toBeVisible();
  expect(requests).toBe(0);
});

test.describe("optional web OIDC", () => {
  test.skip(!enabled, "Stage E feature flag is disabled");

  test("retries one unauthorized BFF read and shows the bound user", async ({
    page,
  }) => {
    let requests = 0;
    await page.route("**/api/bff/me", async (route) => {
      requests += 1;
      if (requests === 1) {
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({
            data: null,
            meta: {},
            error: { code: "AUTH_REQUIRED", message: "Sign in is required" },
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            id: "00000000-0000-4000-8000-000000000001",
            display_name: "阶段 E 测试用户",
            avatar_url: null,
            timezone: "Asia/Shanghai",
            locale: "zh-CN",
            created_at: "2026-09-21T00:00:00Z",
            updated_at: "2026-09-21T00:00:00Z",
          },
          meta: {},
          error: null,
        }),
      });
    });

    await page.goto("/");
    await expect(page.getByText("阶段 E 测试用户")).toBeVisible();
    await expect(page.getByRole("link", { name: "退出" })).toHaveAttribute(
      "href",
      "/sign-out",
    );
    expect(requests).toBe(2);
  });

  test("redirects to sign-in after the single retry also returns 401", async ({
    page,
  }) => {
    let requests = 0;
    await page.route("**/api/bff/me", async (route) => {
      requests += 1;
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          data: null,
          meta: {},
          error: { code: "AUTH_REQUIRED", message: "Sign in is required" },
        }),
      });
    });
    await page.route("**/sign-in", async (route) => {
      await route.fulfill({ status: 200, body: "sign-in" });
    });

    await page.goto("/");
    await expect(page).toHaveURL(/\/sign-in$/);
    // Next.js development Strict Mode can issue one aborted probe before the
    // mounted effect performs its two-request retry sequence.
    expect(requests).toBeGreaterThanOrEqual(2);
    expect(requests).toBeLessThanOrEqual(3);
  });

  test("BFF rejects client-provided identity inputs", async ({ request }) => {
    const queryResponse = await request.get(
      "/api/bff/me?user_id=00000000-0000-4000-8000-000000000001",
    );
    expect(queryResponse.status()).toBe(400);
    expect((await queryResponse.json()).error.code).toBe(
      "IDENTITY_INPUT_REJECTED",
    );

    const headerResponse = await request.get("/api/bff/me", {
      headers: {
        Authorization: "Bearer client-token",
        "x-user-id": "00000000-0000-4000-8000-000000000001",
      },
    });
    expect(headerResponse.status()).toBe(400);
    expect((await headerResponse.json()).error.code).toBe(
      "IDENTITY_INPUT_REJECTED",
    );
  });
});
