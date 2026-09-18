"use client";

import { useSignIn } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { LoginForm } from "./login-form";

export function ClerkLogin() {
  const { signIn, fetchStatus } = useSignIn();
  const router = useRouter();

  return (
    <LoginForm
      busy={fetchStatus === "fetching"}
      onSubmit={async ({ email, password }) => {
        const { error } = await signIn.password({
          emailAddress: email,
          password,
        });
        if (error) throw error;
        if (signIn.status !== "complete") {
          throw new Error("Additional verification is required to finish signing in.");
        }
        await signIn.finalize({
          navigate: ({ decorateUrl }) => {
            const url = decorateUrl("/");
            if (url.startsWith("http")) window.location.href = url;
            else router.push(url);
          },
        });
      }}
    />
  );
}
