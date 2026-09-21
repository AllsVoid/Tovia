export const authRequiredEvent = "tovia:auth-required";

export class AuthRequiredError extends Error {
  constructor() {
    super("Sign in is required");
    this.name = "AuthRequiredError";
  }
}

export function notifyAuthRequired(): void {
  window.dispatchEvent(new Event(authRequiredEvent));
}
