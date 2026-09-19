"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { createWarehouse, listWarehouses, type Warehouse } from "@/features/items/api";
import { MasterDetailWorkspace } from "@/features/workspace/master-detail-workspace";
import { queryKeys } from "@/lib/api/keys";
import { useOrg } from "@/stores/org";

export function WarehousesPage() {
  const orgId = useOrg((s) => s.orgId) ?? "";
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");

  const warehouses = useQuery({
    queryKey: queryKeys.warehouses(orgId),
    enabled: !!orgId,
    queryFn: listWarehouses,
  });

  const create = useMutation({
    mutationFn: createWarehouse,
    onSuccess: async () => {
      setCreating(false);
      setName("");
      await qc.invalidateQueries({ queryKey: queryKeys.warehouses(orgId) });
    },
  });

  return (
    <MasterDetailWorkspace<Warehouse>
      title="Warehouses"
      subtitle="Stock locations"
      items={warehouses.data ?? []}
      getId={(w) => w.id}
      searchPlaceholder="Search warehouses"
      searchText={(w) => w.name}
      loading={warehouses.isPending}
      error={warehouses.error ? "Could not load warehouses." : null}
      emptyLabel="No warehouses yet."
      toolbar={
        <Button type="button" size="sm" className="shrink-0" onClick={() => setCreating(true)}>
          <Plus data-icon="inline-start" />
          New
        </Button>
      }
      renderRow={(w, selected) => (
        <p className={`truncate text-sm font-medium ${selected ? "text-white" : ""}`}>{w.name}</p>
      )}
      renderDetail={(w) => {
        if (creating) {
          return (
            <form
              className="mx-auto w-full max-w-md"
              onSubmit={(e) => {
                e.preventDefault();
                if (!name.trim()) return;
                create.mutate(name.trim());
              }}
            >
              <FieldGroup>
                <h2 className="text-xl font-semibold tracking-tight">New warehouse</h2>
                <Field>
                  <FieldLabel htmlFor="wh-name">Name</FieldLabel>
                  <Input
                    id="wh-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Main"
                    autoFocus
                    required
                  />
                </Field>
                {create.error ? <FieldError>Could not create warehouse.</FieldError> : null}
                <div className="flex gap-2">
                  <Button type="submit" disabled={create.isPending}>
                    {create.isPending ? "Saving…" : "Create"}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setCreating(false)}>
                    Cancel
                  </Button>
                </div>
              </FieldGroup>
            </form>
          );
        }
        if (!w) {
          return (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <p className="text-base font-medium">Select a warehouse</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Preview appears here after you choose a row.
              </p>
            </div>
          );
        }
        return (
          <div className="mx-auto w-full max-w-lg space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Warehouse</p>
              <h2 className="text-xl font-semibold tracking-tight">{w.name}</h2>
            </div>
            <p className="font-mono text-xs break-all text-muted-foreground">{w.id}</p>
          </div>
        );
      }}
    />
  );
}
