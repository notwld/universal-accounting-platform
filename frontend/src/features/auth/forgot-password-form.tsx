"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthShell } from "./auth-shell";
import { authError } from "./errors";
import { PasswordField } from "./password-field";
import {
  forgotEmailSchema,
  resetPasswordSchema,
  verifySchema,
  type ForgotEmailInput,
  type ResetPasswordInput,
} from "./schema";

type Step = "email" | "code" | "password";

export function ForgotPasswordForm({
  step,
  busy,
  onSendCode,
  onVerifyCode,
  onSubmitPassword,
  onBack,
}: {
  step: Step;
  busy?: boolean;
  onSendCode: (email: string) => Promise<void>;
  onVerifyCode: (code: string) => Promise<void>;
  onSubmitPassword: (password: string) => Promise<void>;
  onBack: () => void;
}) {
  const emailForm = useForm<ForgotEmailInput>({
    resolver: zodResolver(forgotEmailSchema),
    defaultValues: { email: "" },
  });
  const codeForm = useForm<{ code: string }>({
    resolver: zodResolver(verifySchema),
    defaultValues: { code: "" },
  });
  const passwordForm = useForm<ResetPasswordInput>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "" },
  });

  const pending =
    busy ||
    emailForm.formState.isSubmitting ||
    codeForm.formState.isSubmitting ||
    passwordForm.formState.isSubmitting;

  const back = (
    <button
      type="button"
      className="font-medium text-foreground underline-offset-4 hover:underline"
      onClick={onBack}
    >
      Back to sign in
    </button>
  );

  if (step === "email") {
    return (
      <AuthShell
        title="Forgot password"
        subtitle="We'll email you a reset code"
        footer={<p>{back}</p>}
      >
        <form
          className="grid gap-4"
          onSubmit={emailForm.handleSubmit(async ({ email }) => {
            try {
              await onSendCode(email);
            } catch (err) {
              emailForm.setError("root", { message: authError(err) });
            }
          })}
        >
          <div className="grid gap-2">
            <Label htmlFor="reset-email">Email</Label>
            <Input
              id="reset-email"
              type="email"
              inputMode="email"
              autoComplete="email"
              autoFocus
              placeholder="you@company.com"
              className="h-10"
              aria-invalid={!!emailForm.formState.errors.email}
              {...emailForm.register("email")}
            />
            {emailForm.formState.errors.email && (
              <p className="text-sm text-destructive">
                {emailForm.formState.errors.email.message}
              </p>
            )}
          </div>
          {emailForm.formState.errors.root && (
            <p className="text-sm text-destructive" role="alert">
              {emailForm.formState.errors.root.message}
            </p>
          )}
          <Button type="submit" className="h-10 w-full" disabled={pending}>
            {pending ? "Sending…" : "Send reset code"}
          </Button>
        </form>
      </AuthShell>
    );
  }

  if (step === "code") {
    return (
      <AuthShell
        title="Check your email"
        subtitle="Enter the reset code we sent you"
        footer={<p>{back}</p>}
      >
        <form
          className="grid gap-4"
          onSubmit={codeForm.handleSubmit(async ({ code }) => {
            try {
              await onVerifyCode(code);
            } catch (err) {
              codeForm.setError("root", { message: authError(err) });
            }
          })}
        >
          <div className="grid gap-2">
            <Label htmlFor="reset-code">Reset code</Label>
            <Input
              id="reset-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              autoFocus
              className="h-10"
              aria-invalid={!!codeForm.formState.errors.code}
              {...codeForm.register("code")}
            />
            {codeForm.formState.errors.code && (
              <p className="text-sm text-destructive">
                {codeForm.formState.errors.code.message}
              </p>
            )}
          </div>
          {codeForm.formState.errors.root && (
            <p className="text-sm text-destructive" role="alert">
              {codeForm.formState.errors.root.message}
            </p>
          )}
          <Button type="submit" className="h-10 w-full" disabled={pending}>
            {pending ? "Verifying…" : "Verify code"}
          </Button>
        </form>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Set a new password"
      subtitle="Choose a password you haven't used before"
      footer={<p>{back}</p>}
    >
      <form
        className="grid gap-4"
        onSubmit={passwordForm.handleSubmit(async ({ password }) => {
          try {
            await onSubmitPassword(password);
          } catch (err) {
            passwordForm.setError("root", { message: authError(err) });
          }
        })}
      >
        <div className="grid gap-2">
          <Label htmlFor="new-password">New password</Label>
          <PasswordField
            id="new-password"
            autoComplete="new-password"
            aria-invalid={!!passwordForm.formState.errors.password}
            {...passwordForm.register("password")}
          />
          <p className="text-xs text-muted-foreground">At least 8 characters.</p>
          {passwordForm.formState.errors.password && (
            <p className="text-sm text-destructive">
              {passwordForm.formState.errors.password.message}
            </p>
          )}
        </div>
        {passwordForm.formState.errors.root && (
          <p className="text-sm text-destructive" role="alert">
            {passwordForm.formState.errors.root.message}
          </p>
        )}
        <Button type="submit" className="h-10 w-full" disabled={pending}>
          {pending ? "Saving…" : "Update password"}
        </Button>
      </form>
    </AuthShell>
  );
}
