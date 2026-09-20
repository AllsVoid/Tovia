import { test, expect } from "@playwright/test";
import { highlightedRegions, contains } from "../src/lib/regions";
import { outlineMapProvider } from "../src/lib/map-provider";
import type { MapPlace, Trip, VisitInput } from "../src/lib/types";
import fs from "node:fs/promises";
import path from "node:path";

test.use({ timezoneId: "Asia/Shanghai" });

for (const future of [false, true]) {
  test(`create ${future ? "future" : "past"} trip, add two regions, open highlighted map`, async ({
    page,
  }) => {
    let trip: Trip | undefined;
    const visits: (VisitInput & { id: string })[] = [];
    const days: {
      id: string;
      trip_id: string;
      date: string;
      title: string | null;
      note: null;
      sort_order: number;
    }[] = [];
    const activities: {
      id: string;
      trip_id: string;
      trip_day_id: string;
      title: string;
      place_id: string | null;
      type: string;
      start_at: null;
      end_at: null;
      status: string;
      note: null;
      sort_order: number;
    }[] = [];
    const places = [
      {
        id: "nanjing",
        canonical_name: "南京市",
        country_code: "CN",
        admin1: "江苏省",
        city: "南京市",
        timezone: "Asia/Shanghai",
        latitude: 32.06,
        longitude: 118.79,
        metadata: { region_id: "cn:3201" },
      },
      {
        id: "suzhou",
        canonical_name: "苏州市",
        country_code: "CN",
        admin1: "江苏省",
        city: "苏州市",
        timezone: "Asia/Shanghai",
        latitude: 31.3,
        longitude: 120.58,
        metadata: { region_id: "cn:3205" },
      },
    ];
    const date = future ? "2099-10-01" : "2024-10-01";
    await page.route("**/api/v1/**", async (route) => {
      const req = route.request(),
        url = new URL(req.url());
      const pathname = url.pathname.replace("/api/v1", "");
      const markers = places
        .filter((p) => visits.some((v) => v.place_id === p.id))
        .map((p) => ({
          ...p,
          region_id: p.metadata.region_id,
          name: p.canonical_name,
          visit_count: future ? 0 : 1,
          upcoming_count: future ? 1 : 0,
          wishlist: false,
          last_visited_at: null,
          next_visit_at: null,
        }));
      let data: unknown;
      if (pathname === "/trips" && req.method() === "POST") {
        trip = { ...req.postDataJSON(), id: "trip-1", summary: null };
        data = trip;
      } else if (pathname === "/trips") data = trip ? [trip] : [];
      else if (pathname === "/trips/trip-1") data = trip;
      else if (pathname === "/trips/trip-1/days" && req.method() === "POST") {
        data = {
          ...req.postDataJSON(),
          id: `day-${days.length}`,
          trip_id: "trip-1",
          title: req.postDataJSON().title ?? null,
          note: null,
          sort_order: 0,
        };
        days.push(data as (typeof days)[number]);
      } else if (pathname === "/trips/trip-1/days") data = days;
      else if (
        pathname === "/trips/trip-1/activities" &&
        req.method() === "POST"
      ) {
        data = {
          ...req.postDataJSON(),
          id: `activity-${activities.length}`,
          trip_id: "trip-1",
          type: "VISIT",
          start_at: null,
          end_at: null,
          status: "PLANNED",
          note: null,
          sort_order: 0,
        };
        activities.push(data as (typeof activities)[number]);
      } else if (pathname === "/trips/trip-1/activities") data = activities;
      else if (pathname === "/visits" && req.method() === "POST") {
        data = { ...req.postDataJSON(), id: `visit-${visits.length}` };
        visits.push(data as (typeof visits)[number]);
      } else if (pathname === "/visits") data = visits;
      else if (pathname === "/calendar/month")
        data = {
          year: Number(date.slice(0, 4)),
          month: Number(date.slice(5, 7)),
          trips: trip ? [trip] : [],
          days: [
            {
              date,
              trip_ids: ["trip-1"],
              places_count: 2,
              visits_count: visits.length,
              activities_count: activities.length,
              has_memory: !future,
            },
          ],
        };
      else if (pathname === "/calendar/day")
        data = {
          date,
          trips: trip ? [trip] : [],
          visits: visits.map((visit) => {
            const place = places.find((item) => item.id === visit.place_id)!;
            return {
              ...visit,
              place_name: place.canonical_name,
              timezone: place.timezone,
            };
          }),
          activities: activities.map((activity) => {
            const place = places.find((item) => item.id === activity.place_id);
            return {
              ...activity,
              place_name: place?.canonical_name ?? null,
              timezone: place?.timezone ?? trip?.timezone ?? "UTC",
            };
          }),
        };
      else if (pathname === "/regions/search") {
        const p = url.searchParams.get("q")?.includes("苏州")
          ? places[1]
          : places[0];
        data = [
          {
            id: p.metadata.region_id,
            name: p.canonical_name,
            path: `江苏省 ${p.canonical_name}`,
          },
        ];
      } else if (
        pathname.includes("/regions/") &&
        pathname.endsWith("/place")
      ) {
        data = pathname.includes("3205") ? places[1] : places[0];
      } else if (pathname.startsWith("/places/"))
        data = places.find((p) => pathname.endsWith(p.id));
      else if (pathname === "/map/summary")
        data = {
          places_count: markers.length,
          visited_places: future ? 0 : markers.length,
          upcoming_places: future ? markers.length : 0,
          wishlist_places: 0,
          visit_count: future ? 0 : visits.length,
          countries_count: 1,
          unknown_country_places: 0,
        };
      else if (pathname === "/map/places")
        data = {
          places: markers,
          total: markers.length,
          limit: 200,
          offset: 0,
        };
      else if (pathname.startsWith("/map/places/")) {
        const p = markers.find((m) => pathname.endsWith(m.id))!;
        data = {
          place: p,
          visits: visits.filter((v) => v.place_id === p.id),
          visits_total: 1,
          wishlist_note: null,
        };
      } else throw new Error(`Unexpected request: ${pathname}`);
      await route.fulfill({ json: { data, meta: {}, error: null } });
    });
    await page.goto("/trips");
    await page.getByRole("button", { name: "新建旅行" }).click();
    await page
      .getByLabel("这次旅行")
      .selectOption(future ? "PLANNING" : "COMPLETED");
    await page.getByLabel("旅行名称").fill("江南两城");
    await page.getByLabel("开始日期").fill(date);
    await page.getByLabel("结束日期").fill(date);
    await page.getByRole("button", { name: "下一步：添加地点" }).click();
    await expect(page.getByRole("heading", { name: "添加城市" })).toBeVisible();
    await expect(page.getByLabel("抵达时间")).toHaveCount(0);
    await page.getByLabel("城市", { exact: true }).fill("南京");
    await page.getByRole("button", { name: /南京市/ }).click();
    await expect(page.getByLabel("抵达时间")).toHaveValue(`${date}T09:00`);
    await expect(page.getByLabel("经度", { exact: true })).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "未至 · 愿望清单" }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "加入旅行" }).click();
    await expect(page.getByText("南京市 已加入旅行并更新地图。")).toBeVisible();
    expect(visits[0].trip_id).toBe("trip-1");
    expect(visits[0].visited_at).toBe(`${date}T01:00:00.000Z`);
    await page.getByRole("button", { name: "继续添加城市" }).click();
    await page.getByLabel("城市", { exact: true }).fill("苏州");
    await page.getByRole("button", { name: /苏州市/ }).click();
    await page.getByRole("button", { name: "加入旅行" }).click();
    await expect(page.getByText("苏州市 已加入旅行并更新地图。")).toBeVisible();
    await page.getByLabel("当天主题").fill("城南漫步");
    await page.getByRole("button", { name: "添加一天" }).click();
    await expect(page.getByText("城南漫步 · 打开日历 ↗")).toBeVisible();
    await page.getByLabel("所属城市").selectOption("nanjing");
    await page.getByLabel("添加当天活动").fill("逛当地市场");
    await page.getByRole("button", { name: "＋ 添加活动" }).click();
    await expect(page.getByText("逛当地市场", { exact: true })).toBeVisible();
    expect(activities[0].place_id).toBe("nanjing");
    await page.screenshot({
      path: `test-results/trip-detail-${future ? "future" : "past"}.png`,
      fullPage: true,
    });
    await page.getByRole("link", { name: "查看地图 →" }).click();
    await expect(page.locator('[data-region-count="2"]')).toBeVisible({
      timeout: 20000,
    });
    await expect(
      page.getByLabel("地点详情").getByRole("heading", { name: "苏州市" }),
    ).toBeVisible();
    await expect(
      page.getByLabel("地点列表").getByText(future ? "将至 1 次" : "曾至 1 次"),
    ).toHaveCount(2);
    await page.screenshot({
      path: `test-results/regions-${future ? "future" : "past"}.png`,
    });
    await page.goto(`/calendar?date=${date}`);
    const nanjingTree = page.getByRole("region", { name: "南京市" });
    await expect(nanjingTree.getByText("逛当地市场 →")).toBeVisible();
    await expect(nanjingTree.getByText(/到访/)).toBeVisible();
    await expect(page.getByText("地点待定")).toHaveCount(0);
    await page.screenshot({
      path: `test-results/calendar-tree-${future ? "future" : "past"}.png`,
      fullPage: true,
    });
  });
}

test("Nanjing uses city polygon, repeated visits share a region, old coordinates still resolve", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (input) =>
    new Response(
      await fs.readFile(
        path.join(process.cwd(), "public", String(input)),
        "utf8",
      ),
    );
  try {
    const place: MapPlace = {
      id: "nanjing",
      name: "南京市",
      country_code: "CN",
      admin1: "江苏省",
      city: "南京市",
      timezone: "Asia/Shanghai",
      latitude: 32.06,
      longitude: 118.79,
      region_id: "cn:3201",
      visit_count: 2,
      upcoming_count: 1,
      wishlist: true,
      last_visited_at: null,
      next_visit_at: null,
    };
    const { data, missing } = await highlightedRegions(
      [place, { ...place, id: "old-poi", region_id: undefined }],
      "all",
      place.id,
    );
    expect(missing).toBe(0);
    expect(data.features).toHaveLength(1);
    const feature = data.features[0];
    expect(feature.properties.id).toBe("cn:3201");
    expect(feature.properties.status).toBe("visited");
    expect(contains(feature, [118.79, 32.06])).toBe(true);
    expect(contains(feature, [120.58, 31.3])).toBe(false);
    expect(
      (await highlightedRegions([place], "upcoming", null)).data.features[0]
        .properties.status,
    ).toBe("upcoming");
    expect(
      outlineMapProvider.style().layers.find((l) => l.id === "places")?.type,
    ).toBe("fill");
    expect(
      outlineMapProvider.style().layers.some((l) => l.type === "circle"),
    ).toBe(false);
  } finally {
    globalThis.fetch = original;
  }
});
