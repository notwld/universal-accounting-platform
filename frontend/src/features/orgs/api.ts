import { api } from "@/lib/api/client";
import type { ApiData } from "@/types/api";

export type OrgItem = {
  id: string;
  name: string;
  status: string;
  finance_setup_complete: boolean;
  finance_role_slug: string | null;
};

export async function bootstrapAuth() {
  await api.post("/auth/bootstrap", { device: { name: "web" } });
}

export async function listOrganizations() {
  const { data } = await api.get<ApiData<{ items: OrgItem[] }>>("/organizations");
  return data.data.items;
}

export async function createOrganization(name: string) {
  const { data } = await api.post<ApiData<{ id: string; name: string; status: string }>>(
    "/organizations",
    { name }
  );
  return data.data;
}
