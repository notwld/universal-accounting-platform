"use client";

import { useSignIn } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ForgotPasswordForm } from "./forgot-password-form";
import { LoginForm } from "./login-form";

type Mode = "login" | "forgot";
type ForgotStep = "email" | "code" | "password";

export function ClerkLogin() {
  const { signIn, fetchStatus } = useSignIn();
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [forgotStep, setForgotStep] = useState<ForgotStep>("email");

  if (mode === "forgot") {
    return (
      <ForgotPasswordForm
        step={forgotStep}
        busy={fetchStatus === "fetching"}
        onBack={() => {
          setMode("login");
          setForgotStep("email");
        }}
        onSendCode={async (email) => {
          const { error: createError } = await signIn.create({ identifier: email });
          if (createError) throw createError;
          const { error: sendError } = await signIn.resetPasswordEmailCode.sendCode();
          if (sendError) throw sendError;
          setForgotStep("code");
        }}
        onVerifyCode={async (code) => {
          const { error } = await signIn.resetPasswordEmailCode.verifyCode({ code });
          if (error) throw error;
          setForgotStep("password");
        }}
        onSubmitPassword={async (password) => {
          const { error } = await signIn.resetPasswordEmailCode.submitPassword({
            password,
            signOutOfOtherSessions: true,
          });
          if (error) throw error;
          if (signIn.status !== "complete") {
            throw new Error("Could not finish resetting your password.");
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

  return (
    <LoginForm
      busy={fetchStatus === "fetching"}
      onForgotPassword={() => {
        setForgotStep("email");
        setMode("forgot");
      }}
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
