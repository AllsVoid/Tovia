import { handleSignIn } from "@logto/next/server-actions";
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
  await handleSignIn(config, request.nextUrl.searchParams);
  redirect("/");
}
