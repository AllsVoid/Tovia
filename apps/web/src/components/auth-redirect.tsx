"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { authRequiredEvent } from "@/lib/auth-events";

export function AuthRedirect() {
  const router = useRouter();
  const redirectStarted = useRef(false);

  useEffect(() => {
    const redirectToSignIn = () => {
      if (redirectStarted.current) return;
      redirectStarted.current = true;
      router.replace("/sign-in");
    };
    window.addEventListener(authRequiredEvent, redirectToSignIn);
    return () =>
      window.removeEventListener(authRequiredEvent, redirectToSignIn);
  }, [router]);

  return null;
}
