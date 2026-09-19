"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  adjustStock,
  listItems,
  listStockBalances,
  listWarehouses,
  type StockBalance,
} from "@/features/items/api";
import { MasterDetailWorkspace } from "@/features/workspace/master-detail-workspace";
import { queryKeys } from "@/lib/api/keys";
import { useOrg } from "@/stores/org";

function balanceId(b: StockBalance) {
  return `${b.warehouse_id}:${b.item_id}`;
}

export function StockAdjustmentsPage() {
  const orgId = useOrg((s) => s.orgId) ?? "";
  const qc = useQueryClient();
  const [qty, setQty] = useState("");
  const [unitCost, setUnitCost] = useState("");
  const [result, setResult] = useState<string | null>(null);

  const balances = useQuery({
    queryKey: queryKeys.stockBalances(orgId),
    enabled: !!orgId,
    queryFn: listStockBalances,
  });
  const items = useQuery({
    queryKey: queryKeys.items(orgId),
    enabled: !!orgId,
    queryFn: listItems,
  });
  const warehouses = useQuery({
    queryKey: queryKeys.warehouses(orgId),
    enabled: !!orgId,
    queryFn: listWarehouses,
  });

  const itemName = useMemo(() => {
    const m = new Map<string, string>();
    for (const i of items.data ?? []) m.set(i.id, i.name);
    return m;
  }, [items.data]);
  const whName = useMemo(() => {
    const m = new Map<string, string>();
    for (const w of warehouses.data ?? []) m.set(w.id, w.name);
    return m;
  }, [warehouses.data]);

  const mutate = useMutation({
    mutationFn: adjustStock,
    onSuccess: async (data) => {
      setResult(`Posted journal ${data.journal_id}`);
      setQty("");
      setUnitCost("");
      await qc.invalidateQueries({ queryKey: queryKeys.stockBalances(orgId) });
    },
  });

  const rows: StockBalance[] =
    (balances.data?.length ? balances.data : null) ??
    (items.data ?? [])
      .filter((i) => i.tracked)
      .map((i) => ({
        item_id: i.id,
        warehouse_id: warehouses.data?.[0]?.id ?? "",
        qty: "0",
        value: "0",
      }))
      .filter((b) => b.warehouse_id);

  return (
    <MasterDetailWorkspace<StockBalance>
      title="Stock Adjustments"
      subtitle="Correct on-hand quantities"
      items={rows}
      getId={balanceId}
      searchPlaceholder="Search item or warehouse"
      searchText={(b) =>
        `${itemName.get(b.item_id) ?? ""} ${whName.get(b.warehouse_id) ?? ""}`
      }
      loading={balances.isPending || items.isPending}
      error={balances.error ? "Could not load stock context." : null}
      emptyLabel="Create a tracked item and warehouse first."
      renderRow={(b, selected) => (
        <div className="min-w-0">
          <p className={`truncate text-sm font-medium ${selected ? "text-white" : ""}`}>
            {itemName.get(b.item_id) ?? b.item_id}
          </p>
          <p
            className={`mt-0.5 truncate text-xs ${selected ? "text-white/80" : "text-muted-foreground"}`}
          >
            {whName.get(b.warehouse_id) ?? "—"} ·{" "}
            <span className="font-mono tabular-nums">{b.qty}</span>
          </p>
        </div>
      )}
      renderDetail={(b) => {
        if (!b) {
          return (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <p className="text-base font-medium">Select a line</p>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground text-pretty">
                Choose an item/warehouse, then enter the adjustment quantity in the form.
              </p>
            </div>
          );
        }
        return (
          <form
            className="mx-auto w-full max-w-md"
            onSubmit={(e) => {
              e.preventDefault();
              if (!qty.trim()) return;
              setResult(null);
              mutate.mutate({
                warehouse_id: b.warehouse_id,
                item_id: b.item_id,
                quantity: qty.trim(),
                unit_cost: unitCost.trim() || undefined,
              });
            }}
          >
            <FieldGroup>
              <div>
                <h2 className="text-xl font-semibold tracking-tight">Adjust stock</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {itemName.get(b.item_id)} @ {whName.get(b.warehouse_id)}
                </p>
              </div>
              <Field>
                <FieldLabel htmlFor="adj-qty">Quantity (signed)</FieldLabel>
                <Input
                  id="adj-qty"
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  placeholder="e.g. 10 or -2"
                  className="font-mono"
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="adj-cost">Unit cost (optional)</FieldLabel>
                <Input
                  id="adj-cost"
                  value={unitCost}
                  onChange={(e) => setUnitCost(e.target.value)}
                  className="font-mono"
                />
              </Field>
              {mutate.error ? (
                <FieldError>
                  Adjustment failed. Check quantity, accounts, and permissions.
                </FieldError>
              ) : null}
              {result ? <p className="text-sm text-muted-foreground">{result}</p> : null}
              <Button type="submit" disabled={mutate.isPending}>
                {mutate.isPending ? "Posting…" : "Post adjustment"}
              </Button>
            </FieldGroup>
          </form>
        );
      }}
    />
  );
}
