"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { authRequiredEvent } from "@/lib/auth-events";

export function AuthRedirect() {
  const router = useRouter();

  useEffect(() => {
    const redirectToSignIn = () => router.replace("/sign-in");
    window.addEventListener(authRequiredEvent, redirectToSignIn);
    return () =>
      window.removeEventListener(authRequiredEvent, redirectToSignIn);
  }, [router]);

  return null;
}
