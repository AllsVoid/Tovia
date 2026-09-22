function required(name) {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required in production`);
  if (value.startsWith("<") && value.endsWith(">")) {
    throw new Error(`${name} must be replaced with a production value`);
  }
  return value;
}

function requireHttps(name) {
  const value = required(name);
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${name} must be an absolute HTTPS URL in production`);
  }
  if (url.protocol !== "https:") {
    throw new Error(`${name} must use HTTPS in production`);
  }
}

try {
  if (process.env.APP_ENV !== "production") process.exit(0);
  if (process.env.NEXT_PUBLIC_WEB_AUTH_MODE !== "oidc") {
    throw new Error("Production requires NEXT_PUBLIC_WEB_AUTH_MODE=oidc");
  }

  requireHttps("LOGTO_ENDPOINT");
  requireHttps("LOGTO_BASE_URL");
  requireHttps("LOGTO_API_RESOURCE");
  required("LOGTO_APP_ID");
  required("LOGTO_APP_SECRET");
  if (required("LOGTO_COOKIE_SECRET").length < 32) {
    throw new Error("LOGTO_COOKIE_SECRET must contain at least 32 characters");
  }
} catch (error) {
  console.error(`Production configuration error: ${error.message}`);
  process.exit(1);
}
