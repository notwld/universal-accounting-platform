import { z } from "zod";

export const loginSchema = z.object({
  email: z.email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export const signupSchema = z.object({
  email: z.email("Enter a valid email"),
  password: z.string().min(8, "Use at least 8 characters"),
});

export const verifySchema = z.object({
  code: z.string().min(4, "Enter the code from your email"),
});

export const forgotEmailSchema = z.object({
  email: z.email("Enter a valid email"),
});

export const resetPasswordSchema = z.object({
  password: z.string().min(8, "Use at least 8 characters"),
});

export type LoginInput = z.infer<typeof loginSchema>;
export type SignupInput = z.infer<typeof signupSchema>;
export type ForgotEmailInput = z.infer<typeof forgotEmailSchema>;
export type ResetPasswordInput = z.infer<typeof resetPasswordSchema>;
