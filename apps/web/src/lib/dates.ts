export function localDate(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
export function localDateTime(date = new Date()): string {
  return `${localDate(date)}T${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}
export function deviceTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}
export function inputToInstant(value: string): string {
  const instant = new Date(value);
  if (
    !Number.isFinite(instant.getTime()) ||
    localDateTime(instant) !== value.slice(0, 16)
  )
    throw new Error("这个本地时间不存在，请检查夏令时或日期。");
  return instant.toISOString();
}
export function formatInstant(value: string, timezone: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}
export const tripStatuses = {
  IDEA: "灵感",
  PLANNING: "规划中",
  BOOKED: "已预订",
  TRAVELING: "旅途中",
  COMPLETED: "已完成",
  ARCHIVED: "已归档",
};
