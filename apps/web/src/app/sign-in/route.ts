import { Prompt } from "@logto/client";
import { signIn } from "@logto/next/server-actions";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { webOidcEnabled } from "@/lib/auth-mode";
import { getLogtoConfig, webAuthUnavailable } from "@/lib/logto";

export async function GET(request: NextRequest) {
  if (!webOidcEnabled) redirect("/");
  let config;
  try {
    config = getLogtoConfig();
  } catch {
    return webAuthUnavailable();
  }
  const reauthentication =
    request.nextUrl.searchParams.get("reauth") === "delete";
  await signIn(config, {
    redirectUri: `${config.baseUrl}/callback`,
    postRedirectUri: reauthentication
      ? `${config.baseUrl}/profile?reauth=delete`
      : config.baseUrl,
    ...(reauthentication ? { prompt: Prompt.Login } : {}),
  });
}
