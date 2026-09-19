"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import {
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

export function StockBalancesPage() {
  const orgId = useOrg((s) => s.orgId) ?? "";

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

  const warehouseOptions = (warehouses.data ?? []).map((w) => ({
    value: w.id,
    label: w.name,
  }));

  return (
    <MasterDetailWorkspace<StockBalance>
      title="Stock Balances"
      subtitle="Quantity on hand by location"
      items={balances.data ?? []}
      getId={balanceId}
      searchPlaceholder="Search item or warehouse"
      searchText={(b) =>
        `${itemName.get(b.item_id) ?? b.item_id} ${whName.get(b.warehouse_id) ?? b.warehouse_id}`
      }
      filterFields={
        warehouseOptions.length
          ? [{ key: "warehouse_id", label: "Warehouse", options: warehouseOptions }]
          : []
      }
      matchFilters={(b, f) => !f.warehouse_id || b.warehouse_id === f.warehouse_id}
      loading={balances.isPending}
      error={balances.error ? "Could not load stock balances." : null}
      emptyLabel="No stock balances yet. Receive or adjust stock first."
      renderRow={(b, selected) => (
        <div className="min-w-0">
          <p className={`truncate text-sm font-medium ${selected ? "text-white" : ""}`}>
            {itemName.get(b.item_id) ?? b.item_id}
          </p>
          <p
            className={`mt-0.5 truncate text-xs ${selected ? "text-white/80" : "text-muted-foreground"}`}
          >
            {whName.get(b.warehouse_id) ?? "Warehouse"} · qty{" "}
            <span className="font-mono tabular-nums">{b.qty}</span>
          </p>
        </div>
      )}
      renderDetail={(b) => {
        if (!b) {
          return (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <p className="text-base font-medium">Select a balance</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Preview quantity and value for the selected row.
              </p>
            </div>
          );
        }
        return (
          <div className="mx-auto w-full max-w-lg space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Stock balance</p>
              <h2 className="text-xl font-semibold tracking-tight">
                {itemName.get(b.item_id) ?? "Item"}
              </h2>
            </div>
            <dl className="grid gap-3 text-sm">
              <div className="grid gap-0.5 border-b pb-2">
                <dt className="text-xs text-muted-foreground">Warehouse</dt>
                <dd>{whName.get(b.warehouse_id) ?? b.warehouse_id}</dd>
              </div>
              <div className="grid gap-0.5 border-b pb-2">
                <dt className="text-xs text-muted-foreground">Quantity</dt>
                <dd className="font-mono tabular-nums text-lg">{b.qty}</dd>
              </div>
              <div className="grid gap-0.5 border-b pb-2">
                <dt className="text-xs text-muted-foreground">Value</dt>
                <dd className="font-mono tabular-nums">{b.value}</dd>
              </div>
            </dl>
          </div>
        );
      }}
    />
  );
}
