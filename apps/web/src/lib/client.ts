import type {
  Activity,
  CalendarDay,
  CalendarMonth,
  MapDetail,
  MapPage,
  MapSummary,
  Place,
  PlaceInput,
  Region,
  PlaceStatus,
  Scope,
  Trip,
  TripDay,
  User,
  Visit,
  VisitInput,
} from "./types";
import { AuthRequiredError, notifyAuthRequired } from "./auth-events";
import { webOidcEnabled } from "./auth-mode";

interface Envelope<T> {
  data: T | null;
  meta: Record<string, unknown>;
  error: { code: string; message: string } | null;
}
export const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const apiBaseUrl = webOidcEnabled ? "/api/bff" : `${apiUrl}/api/v1`;
const messages: Record<string, string> = {
  AUTH_REQUIRED: "请启用本地开发认证，或配置登录服务。",
  RECENT_AUTH_REQUIRED: "请重新登录后再删除账户。",
  ACCOUNT_DELETION_UNAVAILABLE: "账户删除服务尚未配置，请联系管理员。",
  ACCOUNT_PROVIDER_UNAVAILABLE:
    "身份服务暂时不可用；本地数据未删除，请稍后重试。",
  ACCOUNT_DELETION_INCOMPLETE:
    "身份已删除，但本地数据清理未完成，请联系支持人员。",
  DATABASE_UNAVAILABLE: "数据库暂时无法连接，请稍后重试。",
  VALIDATION_ERROR: "请检查必填字段、时区和日期范围。",
  DAY_OUTSIDE_TRIP: "这一天不在旅行日期范围内。",
  DATA_CONFLICT: "这条记录已存在，或关联关系有冲突。",
  TRIP_NOT_FOUND: "旅行不存在或已删除。",
  MAP_PLACE_NOT_FOUND: "你的地图中暂时没有这个地点。",
  REGION_LEVEL_UNSUPPORTED: "请选择这个区县所属的城市。",
};
async function request<T>(
  path: string,
  init?: RequestInit,
  allowEmpty = false,
): Promise<T> {
  let response: Response;
  try {
    for (let attempt = 0; ; attempt += 1) {
      response = await fetch(`${apiBaseUrl}${path}`, {
        ...init,
        headers: { "Content-Type": "application/json", ...init?.headers },
      });
      if (!webOidcEnabled || response.status !== 401) break;
      if (attempt === 0) continue;
      notifyAuthRequired();
      throw new AuthRequiredError();
    }
  } catch (error) {
    if (error instanceof AuthRequiredError) throw error;
    throw new Error("无法连接服务，请确认 API 已启动。");
  }
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || body.error)
    throw new Error(
      messages[body.error?.code ?? ""] ??
        body.error?.message ??
        "请求失败，请稍后重试。",
    );
  if (body.data === null && !allowEmpty) throw new Error("服务返回了空数据。");
  return body.data as T;
}
const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});
async function collect<T>(
  getPage: (offset: number) => Promise<T[]>,
): Promise<T[]> {
  const rows: T[] = [];
  let page: T[];
  do {
    page = await getPage(rows.length);
    rows.push(...page);
  } while (page.length === 50);
  return rows;
}
export const api = {
  me: (signal?: AbortSignal) => request<User>("/me", { signal }),
  updateMe: (input: Pick<User, "display_name" | "timezone" | "locale">) =>
    request<User>("/me", json("PATCH", input)),
  exportData: () => request<Record<string, unknown>>("/me/export"),
  deleteAccount: () =>
    request<void>("/me/delete", json("POST", { confirmation: "DELETE" }), true),
  trips: () =>
    collect((offset) => request<Trip[]>(`/trips?limit=50&offset=${offset}`)),
  trip: (id: string) => request<Trip>(`/trips/${id}`),
  createTrip: (input: {
    title: string;
    start_date: string | null;
    end_date: string | null;
    timezone: string;
    status?: Trip["status"];
  }) => request<Trip>("/trips", json("POST", input)),
  updateTrip: (id: string, input: Partial<Omit<Trip, "id">>) =>
    request<Trip>(`/trips/${id}`, json("PATCH", input)),
  deleteTrip: (id: string) =>
    request<void>(`/trips/${id}`, { method: "DELETE" }, true),
  places: (q: string) =>
    request<Place[]>(`/places/search?q=${encodeURIComponent(q)}&limit=20`),
  place: (id: string) => request<Place>(`/places/${id}`),
  createPlace: (input: PlaceInput) =>
    request<Place>("/places", json("POST", input)),
  regions: (q: string) =>
    request<Region[]>(`/regions/search?q=${encodeURIComponent(q)}`),
  regionPlace: (id: string) =>
    request<Place>(`/regions/${encodeURIComponent(id)}/place`, {
      method: "POST",
    }),
  visits: (tripId: string) =>
    collect((offset) =>
      request<Visit[]>(`/visits?trip_id=${tripId}&limit=50&offset=${offset}`),
    ),
  createVisit: (input: VisitInput) =>
    request<Visit>("/visits", json("POST", input)),
  updateVisit: (id: string, input: Partial<VisitInput>) =>
    request<Visit>(`/visits/${id}`, json("PATCH", input)),
  deleteVisit: (id: string) =>
    request<void>(`/visits/${id}`, { method: "DELETE" }, true),
  days: (id: string) =>
    collect((offset) =>
      request<TripDay[]>(`/trips/${id}/days?limit=50&offset=${offset}`),
    ),
  createDay: (id: string, input: { date: string; title?: string }) =>
    request<TripDay>(`/trips/${id}/days`, json("POST", input)),
  updateDay: (
    id: string,
    input: Partial<Pick<TripDay, "date" | "title" | "note" | "sort_order">>,
  ) => request<TripDay>(`/days/${id}`, json("PATCH", input)),
  deleteDay: (id: string) =>
    request<void>(`/days/${id}`, { method: "DELETE" }, true),
  activities: (id: string) =>
    collect((offset) =>
      request<Activity[]>(`/trips/${id}/activities?limit=50&offset=${offset}`),
    ),
  createActivity: (
    id: string,
    input: {
      trip_day_id: string;
      title: string;
      place_id?: string | null;
      type?: string;
    },
  ) => request<Activity>(`/trips/${id}/activities`, json("POST", input)),
  updateActivity: (
    id: string,
    input: Partial<
      Pick<
        Activity,
        | "trip_day_id"
        | "place_id"
        | "type"
        | "title"
        | "start_at"
        | "end_at"
        | "status"
        | "note"
        | "sort_order"
      >
    >,
  ) => request<Activity>(`/activities/${id}`, json("PATCH", input)),
  deleteActivity: (id: string) =>
    request<void>(`/activities/${id}`, { method: "DELETE" }, true),
  mapPlaces: (scope: Scope, status: PlaceStatus | "all", offset = 0) =>
    request<MapPage>(
      `/map/places?scope=${scope}${status === "all" ? "" : `&status=${status}`}&limit=200&offset=${offset}`,
    ),
  mapSummary: (scope: Scope) =>
    request<MapSummary>(`/map/summary?scope=${scope}`),
  mapDetail: (id: string) => request<MapDetail>(`/map/places/${id}`),
  addWishlist: (placeId: string, note?: string) =>
    request<{ id: string }>(
      "/wishlist",
      json("POST", { place_id: placeId, note }),
    ),
  removeWishlist: (placeId: string) =>
    request<void>(`/wishlist/${placeId}`, { method: "DELETE" }, true),
  calendarMonth: (year: number, month: number) =>
    request<CalendarMonth>(`/calendar/month?year=${year}&month=${month}`),
  calendarDay: (date: string) =>
    request<CalendarDay>(`/calendar/day?date=${date}`),
};
