import { signIn } from "@logto/next/server-actions";
import { redirect } from "next/navigation";
import { webOidcEnabled } from "@/lib/auth-mode";
import { getLogtoConfig, webAuthUnavailable } from "@/lib/logto";

export async function GET() {
  if (!webOidcEnabled) redirect("/");
  let config;
  try {
    config = getLogtoConfig();
  } catch {
    return webAuthUnavailable();
  }
  await signIn(config, {
    redirectUri: `${config.baseUrl}/callback`,
    postRedirectUri: config.baseUrl,
  });
}
