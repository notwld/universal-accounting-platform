import { z } from "zod";

export const env = z
  .object({
    NEXT_PUBLIC_API_URL: z.string().url(),
  })
  .parse({
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  });
