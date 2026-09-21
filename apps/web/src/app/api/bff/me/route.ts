import { getAccessToken } from "@logto/next/server-actions";
import type { NextRequest } from "next/server";
import { webOidcEnabled } from "@/lib/auth-mode";
import {
  getLogtoApiResource,
  getLogtoConfig,
  getToviaApiUrl,
  WebAuthConfigError,
} from "@/lib/logto";

const jsonError = (status: number, code: string, message: string) =>
  Response.json(
    { data: null, meta: {}, error: { code, message } },
    { status, headers: { "Cache-Control": "no-store" } },
  );

export async function GET(request: NextRequest) {
  if (!webOidcEnabled) {
    return jsonError(404, "NOT_FOUND", "Web OIDC is disabled");
  }
  if (
    request.nextUrl.searchParams.size > 0 ||
    request.headers.has("authorization") ||
    request.headers.has("x-user-id")
  ) {
    return jsonError(
      400,
      "IDENTITY_INPUT_REJECTED",
      "Identity credentials are managed by the server session",
    );
  }

  let token: string;
  let apiUrl: string;
  try {
    token = await getAccessToken(getLogtoConfig(), getLogtoApiResource());
    apiUrl = getToviaApiUrl();
  } catch (error) {
    if (error instanceof WebAuthConfigError) {
      return jsonError(
        503,
        "AUTH_UNAVAILABLE",
        "Web authentication is not configured",
      );
    }
    return jsonError(401, "AUTH_REQUIRED", "Sign in is required");
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${apiUrl}/api/v1/me`, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return jsonError(502, "API_UNAVAILABLE", "Tovia API is unavailable");
  }

  return new Response(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type":
        upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
