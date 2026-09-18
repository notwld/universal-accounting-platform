import { ClerkLogin } from "@/features/auth/clerk-login";
import { LoginForm } from "@/features/auth/login-form";

export default function SignInPage() {
  return process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ? (
    <ClerkLogin />
  ) : (
    <LoginForm />
  );
}
