import axios from "axios";
import { env } from "@/lib/env";
import { useOrg } from "@/stores/org";

export const api = axios.create({
  baseURL: env.NEXT_PUBLIC_API_URL,
});

api.interceptors.request.use((config) => {
  const orgId = useOrg.getState().orgId;
  if (orgId) config.headers.set("X-Organization-ID", orgId);
  config.headers.set("X-Request-ID", crypto.randomUUID());
  return config;
});
