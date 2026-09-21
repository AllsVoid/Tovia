import type { User } from "./types";

interface Envelope<T> {
  data: T | null;
  error: { code: string; message: string } | null;
}

export class AuthRequiredError extends Error {
  constructor() {
    super("Sign in is required");
    this.name = "AuthRequiredError";
  }
}

export async function getCurrentUser(signal?: AbortSignal): Promise<User> {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const response = await fetch("/api/bff/me", {
      cache: "no-store",
      credentials: "same-origin",
      signal,
    });

    if (response.status === 401) {
      if (attempt === 0) continue;
      throw new AuthRequiredError();
    }

    const body = (await response.json()) as Envelope<User>;
    if (!response.ok || body.error || !body.data) {
      throw new Error(body.error?.message ?? "登录状态暂时不可用。");
    }
    return body.data;
  }

  throw new AuthRequiredError();
}
