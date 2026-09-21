import "server-only";

import type { LogtoNextConfig } from "@logto/next";
import { webOidcEnabled } from "./auth-mode";

export class WebAuthConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WebAuthConfigError";
  }
}

export function webAuthUnavailable(): Response {
  return Response.json(
    {
      data: null,
      meta: {},
      error: {
        code: "AUTH_UNAVAILABLE",
        message: "Web authentication is not configured",
      },
    },
    { status: 503, headers: { "Cache-Control": "no-store" } },
  );
}

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new WebAuthConfigError(`${name} is required`);
  return value;
}

function httpUrl(name: string): string {
  const value = required(name);
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new WebAuthConfigError(`${name} must be an absolute URL`);
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new WebAuthConfigError(`${name} must use http or https`);
  }
  return value.replace(/\/$/, "");
}

export function getLogtoApiResource(): string {
  return required("LOGTO_API_RESOURCE");
}

export function getToviaApiUrl(): string {
  const value = process.env.TOVIA_API_URL?.trim() || "http://localhost:8000";
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new WebAuthConfigError("TOVIA_API_URL must be an absolute URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new WebAuthConfigError("TOVIA_API_URL must use http or https");
  }
  return value.replace(/\/$/, "");
}

export function getLogtoConfig(): LogtoNextConfig {
  if (!webOidcEnabled) {
    throw new WebAuthConfigError("Web OIDC is disabled");
  }

  const cookieSecret = required("LOGTO_COOKIE_SECRET");
  if (cookieSecret.length < 32) {
    throw new WebAuthConfigError(
      "LOGTO_COOKIE_SECRET must contain at least 32 characters",
    );
  }

  const resource = getLogtoApiResource();
  return {
    endpoint: httpUrl("LOGTO_ENDPOINT"),
    appId: required("LOGTO_APP_ID"),
    appSecret: required("LOGTO_APP_SECRET"),
    baseUrl: httpUrl("LOGTO_BASE_URL"),
    cookieSecret,
    cookieSecure: process.env.NODE_ENV === "production",
    resources: [resource],
  };
}
