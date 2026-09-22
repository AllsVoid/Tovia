import { expect, test } from "@playwright/test";
import { apiPath, apiPattern } from "./api-route";

test.use({ timezoneId: "Asia/Hong_Kong" });

test("edits a visit and an activity without recreating either record", async ({
  page,
}) => {
  const trip = {
    id: "trip-1",
    title: "京都小旅行",
    status: "PLANNING",
    start_date: "2026-10-02",
    end_date: "2026-10-03",
    timezone: "Asia/Tokyo",
    summary: null,
  };
  const place = {
    id: "place-1",
    canonical_name: "京都",
    country_code: "JP",
    city: "京都",
    timezone: "Asia/Tokyo",
    latitude: 35.01,
    longitude: 135.76,
  };
  const visit = {
    id: "visit-1",
    place_id: place.id,
    trip_id: trip.id,
    trip_day_id: "day-1",
    visited_at: "2026-10-02T01:00:00Z",
    ended_at: null,
    note: null,
  };
  const days = [
    { id: "day-1", trip_id: trip.id, date: "2026-10-02", title: "抵达" },
    { id: "day-2", trip_id: trip.id, date: "2026-10-03", title: "游览" },
  ];
  const activity = {
    id: "activity-1",
    trip_id: trip.id,
    trip_day_id: "day-1",
    place_id: place.id,
    type: "VISIT",
    title: "寺庙散步",
    start_at: null,
    end_at: null,
    status: "PLANNED",
    sort_order: 0,
    note: null,
  };
  const patches: { path: string; body: Record<string, unknown> }[] = [];

  await page.route(apiPattern, async (route) => {
    const request = route.request();
    const path = apiPath(request.url());
    let data: unknown;
    if (path === `/trips/${trip.id}`) data = trip;
    else if (path === `/trips/${trip.id}/days`) data = days;
    else if (path === `/trips/${trip.id}/activities`) data = [activity];
    else if (path === "/visits") data = [visit];
    else if (path === "/trips") data = [trip];
    else if (path === `/places/${place.id}`) data = place;
    else if (path === "/visits/visit-1" && request.method() === "PATCH") {
      const body = request.postDataJSON() as Record<string, unknown>;
      patches.push({ path, body });
      Object.assign(visit, body);
      data = visit;
    } else if (
      path === "/activities/activity-1" &&
      request.method() === "PATCH"
    ) {
      const body = request.postDataJSON() as Record<string, unknown>;
      patches.push({ path, body });
      Object.assign(activity, body);
      data = activity;
    } else {
      throw new Error(
        `Unexpected trip API request: ${request.method()} ${path}`,
      );
    }
    await route.fulfill({ json: { data, meta: {}, error: null } });
  });

  await page.goto(`/trips/${trip.id}`);
  await page.getByRole("button", { name: "编辑", exact: true }).first().click();
  await page.getByLabel("抵达时间（设备时区）").fill("2026-10-02T12:00");
  await page.getByLabel("备注", { exact: true }).first().fill("补录访问记录");
  await page.getByRole("button", { name: "保存访问记录" }).click();
  await expect(page.getByText("补录访问记录")).toBeVisible();

  const activityRow = page.locator("li").filter({ hasText: "寺庙散步" });
  await activityRow.getByRole("button", { name: "编辑" }).click();
  await activityRow.getByLabel("标题").fill("清晨散步");
  await activityRow.getByLabel("日期").selectOption("day-2");
  await activityRow.getByLabel("类型").selectOption("FOOD");
  await activityRow.getByLabel("开始时间（设备时区）").fill("2026-10-03T08:30");
  await activityRow.getByLabel("备注").fill("早餐后出发");
  await activityRow.getByRole("button", { name: "保存活动" }).click();
  await expect(page.getByText("清晨散步")).toBeVisible();

  expect(patches).toHaveLength(2);
  expect(patches[0].body).toMatchObject({
    trip_id: trip.id,
    trip_day_id: "day-1",
    note: "补录访问记录",
    visited_at: "2026-10-02T04:00:00.000Z",
  });
  expect(patches[1].body).toMatchObject({
    title: "清晨散步",
    trip_day_id: "day-2",
    type: "FOOD",
    note: "早餐后出发",
    start_at: "2026-10-03T00:30:00.000Z",
  });
});
