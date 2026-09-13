import { test, expect } from "@playwright/test";

test.use({ timezoneId: "Asia/Shanghai" });

test("record a place, revisit it, and open its calendar memory", async ({
  page,
}) => {
  const place = {
    id: "place-1",
    canonical_name: "大理古城",
    country_code: "CN",
    city: "大理",
    admin1: null,
    timezone: "Asia/Shanghai",
    latitude: 25.69,
    longitude: 100.16,
  };
  const visits: Record<string, unknown>[] = [];
  let saved = false;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api/v1", "");
    let data: unknown;
    const marker = {
      ...place,
      name: place.canonical_name,
      visit_count: visits.length,
      upcoming_count: 0,
      wishlist: false,
      last_visited_at: visits.length ? visits[0].visited_at : null,
      next_visit_at: null,
    };
    if (path === "/places" && request.method() === "POST") {
      saved = true;
      data = place;
    } else if (path === "/places/search") data = saved ? [place] : [];
    else if (path === "/trips") data = [];
    else if (path === "/visits" && request.method() === "POST") {
      data = {
        ...request.postDataJSON(),
        id: `visit-${visits.length}`,
        trip_id: null,
        trip_day_id: null,
        ended_at: null,
      };
      visits.push(data as Record<string, unknown>);
    } else if (path === "/map/summary")
      data = {
        places_count: visits.length ? 1 : 0,
        visited_places: visits.length ? 1 : 0,
        upcoming_places: 0,
        wishlist_places: 0,
        visit_count: visits.length,
        countries_count: visits.length ? 1 : 0,
        unknown_country_places: 0,
      };
    else if (path === "/map/places")
      data = {
        places: visits.length ? [marker] : [],
        total: visits.length ? 1 : 0,
        limit: 200,
        offset: 0,
      };
    else if (path === "/map/places/place-1")
      data = {
        place: marker,
        visits,
        visits_total: visits.length,
        wishlist_note: null,
      };
    else if (path === "/calendar/month")
      data = {
        year: 2024,
        month: 2,
        trips: [],
        days: [
          {
            date: "2024-02-29",
            trip_ids: [],
            visits_count: visits.length,
            places_count: 1,
            activities_count: 0,
            has_memory: true,
          },
        ],
      };
    else if (path === "/calendar/day")
      data = {
        date: "2024-02-29",
        trips: [],
        activities: [],
        visits: visits.map((v) => ({
          ...v,
          place_name: place.canonical_name,
          timezone: place.timezone,
        })),
      };
    else throw new Error(`Unexpected request ${path}`);
    await route.fulfill({ json: { data, meta: {}, error: null } });
  });
  await page.goto("/");
  await expect(page.locator('[data-ready="true"]')).toBeVisible({
    timeout: 15000,
  });
  await page.getByRole("button", { name: "＋ 记录地点" }).click();
  await page.getByRole("button", { name: "手工添加地点" }).click();
  await page.getByLabel("地点名称", { exact: true }).fill("大理古城");
  await page.getByLabel("经度", { exact: true }).fill("100.16");
  await page.getByLabel("纬度", { exact: true }).fill("25.69");
  await page.getByRole("button", { name: "保存并选择地点" }).click();
  await page.getByLabel("抵达时间").fill("2024-02-29T09:00");
  await page.getByRole("button", { name: "保存访问记录" }).click();
  await expect(
    page.getByLabel("地点列表").getByText("曾至 1 次"),
  ).toBeVisible();
  expect(visits[0].visited_at).toBe("2024-02-29T01:00:00.000Z");
  await page.getByLabel("地点列表").getByRole("button").click();
  await page.getByRole("button", { name: "添加访问", exact: true }).click();
  await page.getByLabel("抵达时间").fill("2024-02-29T15:00");
  await page.getByRole("button", { name: "保存访问记录" }).click();
  await expect(
    page.getByLabel("地点列表").getByText("曾至 2 次"),
  ).toBeVisible();
  await expect(page.getByLabel("地点列表").getByRole("button")).toHaveCount(1);
  await page.goto("/calendar?date=2024-02-29");
  await expect(
    page.getByLabel("当天记录").getByRole("link", { name: "大理古城" }),
  ).toHaveCount(2);
  await page
    .getByLabel("当天记录")
    .getByRole("link", { name: "大理古城" })
    .first()
    .click();
  await expect(
    page.getByLabel("地点详情").getByRole("heading", { name: "大理古城" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
