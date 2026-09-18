"use client";

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthShell } from "./auth-shell";
import { authError } from "./errors";
import { PasswordField } from "./password-field";
import { signupSchema, verifySchema, type SignupInput } from "./schema";

export function SignupForm({
  onSubmit,
  onVerify,
  step = "start",
  busy,
}: {
  onSubmit?: (values: SignupInput) => Promise<void>;
  onVerify?: (code: string) => Promise<void>;
  step?: "start" | "verify";
  busy?: boolean;
}) {
  const form = useForm<SignupInput>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", password: "" },
  });
  const verify = useForm<{ code: string }>({
    resolver: zodResolver(verifySchema),
    defaultValues: { code: "" },
  });
  const pending = busy || form.formState.isSubmitting || verify.formState.isSubmitting;

  if (step === "verify") {
    return (
      <AuthShell
        title="Check your email"
        subtitle="Enter the verification code we sent you"
        footer={
          <p>
            Wrong email?{" "}
            <Link href="/sign-up" className="font-medium text-foreground underline-offset-4 hover:underline">
              Start over
            </Link>
          </p>
        }
      >
        <form
          className="grid gap-4"
          onSubmit={verify.handleSubmit(async ({ code }) => {
            try {
              if (!onVerify) throw new Error("Verification is not available.");
              await onVerify(code);
            } catch (err) {
              verify.setError("root", { message: authError(err) });
            }
          })}
        >
          <div className="grid gap-2">
            <Label htmlFor="code">Verification code</Label>
            <Input
              id="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              autoFocus
              className="h-10"
              aria-invalid={!!verify.formState.errors.code}
              {...verify.register("code")}
            />
            {verify.formState.errors.code && (
              <p className="text-sm text-destructive">
                {verify.formState.errors.code.message}
              </p>
            )}
          </div>
          {verify.formState.errors.root && (
            <p className="text-sm text-destructive" role="alert">
              {verify.formState.errors.root.message}
            </p>
          )}
          <Button type="submit" className="h-10 w-full" disabled={pending}>
            {pending ? "Verifying…" : "Verify"}
          </Button>
        </form>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start with your work email"
      footer={
        <p>
          Already have an account?{" "}
          <Link href="/sign-in" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <form
        className="grid gap-4"
        onSubmit={form.handleSubmit(async (values) => {
          try {
            if (!onSubmit) {
              throw new Error(
                "Add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY to frontend/.env.local"
              );
            }
            await onSubmit(values);
          } catch (err) {
            form.setError("root", { message: authError(err) });
          }
        })}
      >
        <div className="grid gap-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            autoFocus
            placeholder="you@company.com"
            className="h-10"
            aria-invalid={!!form.formState.errors.email}
            {...form.register("email")}
          />
          {form.formState.errors.email && (
            <p className="text-sm text-destructive">
              {form.formState.errors.email.message}
            </p>
          )}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="password">Password</Label>
          <PasswordField
            id="password"
            autoComplete="new-password"
            aria-invalid={!!form.formState.errors.password}
            {...form.register("password")}
          />
          <p className="text-xs text-muted-foreground">At least 8 characters.</p>
          {form.formState.errors.password && (
            <p className="text-sm text-destructive">
              {form.formState.errors.password.message}
            </p>
          )}
        </div>
        {form.formState.errors.root && (
          <p className="text-sm text-destructive" role="alert">
            {form.formState.errors.root.message}
          </p>
        )}
        <Button type="submit" className="h-10 w-full" disabled={pending}>
          {pending ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthShell>
  );
}
