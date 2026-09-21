"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthRequiredError } from "@/lib/auth-events";
import { api } from "@/lib/client";
import type { User } from "@/lib/types";

type AuthState =
  | { status: "loading" }
  | { status: "authenticated"; user: User }
  | { status: "error" };

export function AuthStatus() {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    api
      .me(controller.signal)
      .then((user) => setState({ status: "authenticated", user }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        if (error instanceof AuthRequiredError) return;
        setState({ status: "error" });
      });
    return () => controller.abort();
  }, []);

  if (state.status === "loading") {
    return <span role="status">正在确认登录…</span>;
  }
  if (state.status === "error") {
    return (
      <Link href="/sign-in" prefetch={false}>
        登录
      </Link>
    );
  }
  return (
    <span className="auth-status">
      <span title={state.user.id}>{state.user.display_name}</span>
      <Link href="/sign-out" prefetch={false}>
        退出
      </Link>
    </span>
  );
}
