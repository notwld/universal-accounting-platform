"use client";

import { useState } from "react";
import { useSignUp } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { SignupForm } from "./signup-form";

export function ClerkSignup() {
  const { signUp, fetchStatus } = useSignUp();
  const router = useRouter();
  const [step, setStep] = useState<"start" | "verify">("start");

  return (
    <SignupForm
      busy={fetchStatus === "fetching"}
      step={step}
      onSubmit={async ({ email, password }) => {
        const { error } = await signUp.password({ emailAddress: email, password });
        if (error) throw error;
        await signUp.verifications.sendEmailCode();
        setStep("verify");
      }}
      onVerify={async (code) => {
        const { error } = await signUp.verifications.verifyEmailCode({ code });
        if (error) throw error;
        if (signUp.status !== "complete") {
          throw new Error("Could not verify that code.");
        }
        await signUp.finalize({
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
