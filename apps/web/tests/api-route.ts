export const oidcTestEnabled = process.env.NEXT_PUBLIC_WEB_AUTH_MODE === "oidc";

export const apiPattern = oidcTestEnabled ? "**/api/bff/**" : "**/api/v1/**";

export function apiPath(url: string): string {
  return decodeURIComponent(new URL(url).pathname).replace(
    oidcTestEnabled ? "/api/bff" : "/api/v1",
    "",
  );
}

export const currentUser = {
  id: "00000000-0000-4000-8000-000000000001",
  display_name: "阶段 F 测试用户",
  avatar_url: null,
  timezone: "Asia/Shanghai",
  locale: "zh-CN",
  created_at: "2026-09-21T00:00:00Z",
  updated_at: "2026-09-21T00:00:00Z",
};
