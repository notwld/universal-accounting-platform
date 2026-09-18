import { ClerkSignup } from "@/features/auth/clerk-signup";
import { SignupForm } from "@/features/auth/signup-form";

export default function SignUpPage() {
  return process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ? (
    <ClerkSignup />
  ) : (
    <SignupForm />
  );
}
