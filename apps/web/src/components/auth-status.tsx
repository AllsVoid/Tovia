"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthRequiredError, getCurrentUser } from "@/lib/bff-client";
import type { User } from "@/lib/types";

type AuthState =
  | { status: "loading" }
  | { status: "authenticated"; user: User }
  | { status: "error" };

export function AuthStatus() {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getCurrentUser(controller.signal)
      .then((user) => setState({ status: "authenticated", user }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        if (error instanceof AuthRequiredError) {
          router.replace("/sign-in");
          return;
        }
        setState({ status: "error" });
      });
    return () => controller.abort();
  }, [router]);

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
