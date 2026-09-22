import { randomUUID } from "node:crypto";
import { getAccessToken } from "@logto/next/server-actions";
import type { NextRequest } from "next/server";
import { webOidcEnabled } from "@/lib/auth-mode";
import {
  getLogtoApiResource,
  getLogtoConfig,
  getToviaApiUrl,
  WebAuthConfigError,
} from "@/lib/logto";

type Rule = {
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: RegExp;
  query?: ReadonlySet<string>;
};

const pageQuery = new Set(["limit", "offset"]);
const rules: Rule[] = [
  { method: "GET", path: /^me$/ },
  { method: "GET", path: /^trips$/, query: pageQuery },
  { method: "POST", path: /^trips$/ },
  { method: "GET", path: /^trips\/[a-zA-Z0-9_-]+$/ },
  { method: "PATCH", path: /^trips\/[a-zA-Z0-9_-]+$/ },
  { method: "DELETE", path: /^trips\/[a-zA-Z0-9_-]+$/ },
  {
    method: "GET",
    path: /^trips\/[a-zA-Z0-9_-]+\/days$/,
    query: pageQuery,
  },
  { method: "POST", path: /^trips\/[a-zA-Z0-9_-]+\/days$/ },
  {
    method: "GET",
    path: /^trips\/[a-zA-Z0-9_-]+\/activities$/,
    query: pageQuery,
  },
  { method: "POST", path: /^trips\/[a-zA-Z0-9_-]+\/activities$/ },
  { method: "DELETE", path: /^days\/[a-zA-Z0-9_-]+$/ },
  { method: "DELETE", path: /^activities\/[a-zA-Z0-9_-]+$/ },
  {
    method: "GET",
    path: /^places\/search$/,
    query: new Set(["q", "limit", "offset"]),
  },
  { method: "POST", path: /^places$/ },
  { method: "GET", path: /^places\/[a-zA-Z0-9_-]+$/ },
  {
    method: "GET",
    path: /^regions\/search$/,
    query: new Set(["q"]),
  },
  { method: "POST", path: /^regions\/[a-zA-Z0-9:_-]+\/place$/ },
  {
    method: "GET",
    path: /^visits$/,
    query: new Set(["trip_id", "limit", "offset"]),
  },
  { method: "POST", path: /^visits$/ },
  { method: "DELETE", path: /^visits\/[a-zA-Z0-9_-]+$/ },
  {
    method: "GET",
    path: /^map\/places$/,
    query: new Set(["scope", "status", "limit", "offset"]),
  },
  {
    method: "GET",
    path: /^map\/summary$/,
    query: new Set(["scope"]),
  },
  { method: "GET", path: /^map\/places\/[a-zA-Z0-9_-]+$/ },
  { method: "POST", path: /^wishlist$/ },
  { method: "DELETE", path: /^wishlist\/[a-zA-Z0-9_-]+$/ },
  {
    method: "GET",
    path: /^calendar\/month$/,
    query: new Set(["year", "month"]),
  },
  {
    method: "GET",
    path: /^calendar\/day$/,
    query: new Set(["date"]),
  },
];

const jsonError = (
  status: number,
  code: string,
  message: string,
  requestId = randomUUID(),
) =>
  Response.json(
    { data: null, meta: {}, error: { code, message } },
    {
      status,
      headers: { "Cache-Control": "no-store", "X-Request-ID": requestId },
    },
  );

function isIdentityKey(key: string): boolean {
  const normalized = key.toLowerCase().replaceAll(/[^a-z0-9]/g, "");
  return normalized === "userid" || normalized === "xuserid";
}

function hasIdentityInput(value: unknown): boolean {
  if (Array.isArray(value)) return value.some(hasIdentityInput);
  if (!value || typeof value !== "object") return false;
  return Object.entries(value).some(([key, child]) => {
    return isIdentityKey(key) || hasIdentityInput(child);
  });
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const requestId = randomUUID();
  if (!webOidcEnabled) {
    return jsonError(404, "NOT_FOUND", "Web OIDC is disabled", requestId);
  }
  if (
    request.headers.has("authorization") ||
    request.headers.has("x-user-id")
  ) {
    return jsonError(
      400,
      "IDENTITY_INPUT_REJECTED",
      "Identity credentials are managed by the server session",
      requestId,
    );
  }

  const { path: segments } = await context.params;
  const path = segments.join("/");
  const rule = rules.find(
    (candidate) =>
      candidate.method === request.method && candidate.path.test(path),
  );
  if (!rule) return jsonError(404, "NOT_FOUND", "BFF route is not available");

  for (const key of request.nextUrl.searchParams.keys()) {
    if (isIdentityKey(key)) {
      return jsonError(
        400,
        "IDENTITY_INPUT_REJECTED",
        "Identity credentials are managed by the server session",
        requestId,
      );
    }
    if (!rule.query?.has(key)) {
      return jsonError(
        400,
        "QUERY_REJECTED",
        "Query parameter is not allowed",
        requestId,
      );
    }
  }

  let body: string | undefined;
  if (request.method === "POST" || request.method === "PATCH") {
    body = await request.text();
    if (body.length > 1_000_000) {
      return jsonError(
        413,
        "PAYLOAD_TOO_LARGE",
        "Request body is too large",
        requestId,
      );
    }
    if (body) {
      let payload: unknown;
      try {
        payload = JSON.parse(body);
      } catch {
        return jsonError(
          400,
          "INVALID_JSON",
          "Request body must be valid JSON",
          requestId,
        );
      }
      if (hasIdentityInput(payload)) {
        return jsonError(
          400,
          "IDENTITY_INPUT_REJECTED",
          "Identity credentials are managed by the server session",
          requestId,
        );
      }
    }
  }

  let token: string;
  let apiUrl: string;
  try {
    token = await getAccessToken(getLogtoConfig(), getLogtoApiResource());
    apiUrl = getToviaApiUrl();
  } catch (error) {
    if (error instanceof WebAuthConfigError) {
      console.warn(
        JSON.stringify({
          event: "auth.session",
          outcome: "unavailable",
          reason: "configuration_missing",
          request_id: requestId,
        }),
      );
      return jsonError(
        503,
        "AUTH_UNAVAILABLE",
        "Web authentication is not configured",
        requestId,
      );
    }
    console.warn(
      JSON.stringify({
        event: "auth.session",
        outcome: "denied",
        reason: "session_unavailable",
        request_id: requestId,
      }),
    );
    return jsonError(401, "AUTH_REQUIRED", "Sign in is required", requestId);
  }

  let upstream: Response;
  try {
    upstream = await fetch(
      `${apiUrl}/api/v1/${path}${request.nextUrl.search}`,
      {
        method: request.method,
        body,
        cache: "no-store",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
          ...(body ? { "Content-Type": "application/json" } : {}),
        },
        signal: AbortSignal.timeout(10_000),
      },
    );
  } catch {
    return jsonError(
      502,
      "API_UNAVAILABLE",
      "Tovia API is unavailable",
      requestId,
    );
  }

  return new Response(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type":
        upstream.headers.get("content-type") ?? "application/json",
      "X-Request-ID": upstream.headers.get("x-request-id") ?? requestId,
    },
  });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
