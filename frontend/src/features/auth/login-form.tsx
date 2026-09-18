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
import { loginSchema, type LoginInput } from "./schema";

export function LoginForm({
  onSubmit,
  onForgotPassword,
  busy,
}: {
  onSubmit?: (values: LoginInput) => Promise<void>;
  onForgotPassword?: () => void;
  busy?: boolean;
}) {
  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = form;
  const pending = busy || isSubmitting;

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to continue"
      footer={
        <p>
          New here?{" "}
          <Link href="/sign-up" className="font-medium text-foreground underline-offset-4 hover:underline">
            Create an account
          </Link>
        </p>
      }
    >
      <form
        className="grid gap-4"
        onSubmit={handleSubmit(async (values) => {
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
            aria-invalid={!!errors.email}
            {...register("email")}
          />
          {errors.email && (
            <p className="text-sm text-destructive">{errors.email.message}</p>
          )}
        </div>
        <div className="grid gap-2">
          <div className="flex items-center justify-between gap-2">
            <Label htmlFor="password">Password</Label>
            {onForgotPassword && (
              <button
                type="button"
                className="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                onClick={onForgotPassword}
              >
                Forgot password?
              </button>
            )}
          </div>
          <PasswordField
            id="password"
            autoComplete="current-password"
            aria-invalid={!!errors.password}
            {...register("password")}
          />
          {errors.password && (
            <p className="text-sm text-destructive">{errors.password.message}</p>
          )}
        </div>
        {errors.root && (
          <p className="text-sm text-destructive" role="alert">
            {errors.root.message}
          </p>
        )}
        <Button type="submit" className="h-10 w-full" disabled={pending}>
          {pending ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthShell>
  );
}
