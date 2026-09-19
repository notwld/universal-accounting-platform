"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  listItems,
  listStockBalances,
  listWarehouses,
  transferStock,
  type StockBalance,
} from "@/features/items/api";
import { MasterDetailWorkspace } from "@/features/workspace/master-detail-workspace";
import { queryKeys } from "@/lib/api/keys";
import { useOrg } from "@/stores/org";

function balanceId(b: StockBalance) {
  return `${b.warehouse_id}:${b.item_id}`;
}

export function StockTransfersPage() {
  const orgId = useOrg((s) => s.orgId) ?? "";
  const qc = useQueryClient();
  const [toWarehouseId, setToWarehouseId] = useState("");
  const [qty, setQty] = useState("");
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
    mutationFn: transferStock,
    onSuccess: async () => {
      setResult("Transfer posted.");
      setQty("");
      await qc.invalidateQueries({ queryKey: queryKeys.stockBalances(orgId) });
    },
  });

  return (
    <MasterDetailWorkspace<StockBalance>
      title="Stock Transfers"
      subtitle="Move stock between warehouses"
      items={balances.data ?? []}
      getId={balanceId}
      searchPlaceholder="Search item or warehouse"
      searchText={(b) =>
        `${itemName.get(b.item_id) ?? ""} ${whName.get(b.warehouse_id) ?? ""}`
      }
      loading={balances.isPending}
      error={balances.error ? "Could not load stock balances." : null}
      emptyLabel="No balances to transfer from. Adjust stock first."
      renderRow={(b, selected) => (
        <div className="min-w-0">
          <p className={`truncate text-sm font-medium ${selected ? "text-white" : ""}`}>
            {itemName.get(b.item_id) ?? b.item_id}
          </p>
          <p
            className={`mt-0.5 truncate text-xs ${selected ? "text-white/80" : "text-muted-foreground"}`}
          >
            From {whName.get(b.warehouse_id) ?? "—"} ·{" "}
            <span className="font-mono tabular-nums">{b.qty}</span>
          </p>
        </div>
      )}
      renderDetail={(b) => {
        if (!b) {
          return (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <p className="text-base font-medium">Select a source balance</p>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground text-pretty">
                Pick the from-location row, then choose a destination warehouse and quantity.
              </p>
            </div>
          );
        }
        const destinations = (warehouses.data ?? []).filter((w) => w.id !== b.warehouse_id);
        return (
          <form
            className="mx-auto w-full max-w-md"
            onSubmit={(e) => {
              e.preventDefault();
              if (!toWarehouseId || !qty.trim()) return;
              setResult(null);
              mutate.mutate({
                from_warehouse_id: b.warehouse_id,
                to_warehouse_id: toWarehouseId,
                item_id: b.item_id,
                quantity: qty.trim(),
              });
            }}
          >
            <FieldGroup>
              <div>
                <h2 className="text-xl font-semibold tracking-tight">Transfer stock</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {itemName.get(b.item_id)} from {whName.get(b.warehouse_id)}
                </p>
              </div>
              <Field>
                <FieldLabel>To warehouse</FieldLabel>
                <Select
                  value={toWarehouseId || undefined}
                  onValueChange={(v) => setToWarehouseId(String(v ?? ""))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select…" />
                  </SelectTrigger>
                  <SelectContent>
                    {destinations.map((w) => (
                      <SelectItem key={w.id} value={w.id}>
                        {w.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel htmlFor="xfer-qty">Quantity</FieldLabel>
                <Input
                  id="xfer-qty"
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  className="font-mono"
                  required
                />
              </Field>
              {mutate.error ? (
                <FieldError>Transfer failed. Check quantity and destinations.</FieldError>
              ) : null}
              {result ? <p className="text-sm text-muted-foreground">{result}</p> : null}
              <Button type="submit" disabled={mutate.isPending || !toWarehouseId}>
                {mutate.isPending ? "Posting…" : "Post transfer"}
              </Button>
            </FieldGroup>
          </form>
        );
      }}
    />
  );
}
