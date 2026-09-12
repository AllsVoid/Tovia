export type TripStatus =
  "IDEA" | "PLANNING" | "BOOKED" | "TRAVELING" | "COMPLETED" | "ARCHIVED";
export interface Trip {
  id: string;
  title: string;
  status: TripStatus;
  start_date: string | null;
  end_date: string | null;
  timezone: string;
  summary: string | null;
}
export interface Envelope<T> {
  data: T | null;
  meta: Record<string, unknown>;
  error: { code: string; message: string } | null;
}
export const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || body.error)
    throw new Error(body.error?.message ?? "请求失败，请稍后再试");
  if (body.data === null) throw new Error("服务返回了空数据");
  return body.data;
}
export const api = {
  trips: () => request<Trip[]>("/trips"),
  createTrip: (input: {
    title: string;
    start_date: string | null;
    end_date: string | null;
    timezone: string;
  }) =>
    request<Trip>("/trips", { method: "POST", body: JSON.stringify(input) }),
};
