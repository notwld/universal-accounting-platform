"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createItem, listAccounts, listItems, type FinanceItem } from "@/features/items/api";
import { MasterDetailWorkspace } from "@/features/workspace/master-detail-workspace";
import { queryKeys } from "@/lib/api/keys";
import { useOrg } from "@/stores/org";

export function ItemsPage() {
  const orgId = useOrg((s) => s.orgId) ?? "";
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);

  const items = useQuery({
    queryKey: queryKeys.items(orgId),
    enabled: !!orgId,
    queryFn: listItems,
  });
  const accounts = useQuery({
    queryKey: queryKeys.accounts(orgId),
    enabled: !!orgId && creating,
    queryFn: listAccounts,
  });

  const create = useMutation({
    mutationFn: createItem,
    onSuccess: async () => {
      setCreating(false);
      await qc.invalidateQueries({ queryKey: queryKeys.items(orgId) });
    },
  });

  const incomeOptions = useMemo(() => accounts.data ?? [], [accounts.data]);

  return (
    <MasterDetailWorkspace<FinanceItem>
      title="Items"
      subtitle="Products and services"
      items={items.data ?? []}
      getId={(i) => i.id}
      searchPlaceholder="Search SKU or name"
      searchText={(i) => `${i.sku} ${i.name}`}
      filterFields={[
        {
          key: "kind",
          label: "Kind",
          options: [
            { value: "good", label: "Good" },
            { value: "service", label: "Service" },
          ],
        },
        {
          key: "tracked",
          label: "Stock tracked",
          options: [
            { value: "true", label: "Tracked" },
            { value: "false", label: "Not tracked" },
          ],
        },
      ]}
      matchFilters={(item, f) => {
        if (f.kind && item.kind !== f.kind) return false;
        if (f.tracked === "true" && !item.tracked) return false;
        if (f.tracked === "false" && item.tracked) return false;
        return true;
      }}
      loading={items.isPending}
      error={items.error ? "Could not load items." : null}
      emptyLabel="No items yet. Create one to get started."
      toolbar={
        <Button type="button" size="sm" className="shrink-0" onClick={() => setCreating(true)}>
          <Plus data-icon="inline-start" />
          New
        </Button>
      }
      renderRow={(item, selected) => (
        <div className="min-w-0">
          <p className={`truncate text-sm font-medium ${selected ? "text-white" : ""}`}>
            {item.name}
          </p>
          <p
            className={`mt-0.5 truncate font-mono text-xs ${selected ? "text-white/80" : "text-muted-foreground"}`}
          >
            {item.sku} · {item.kind}
            {item.tracked ? " · tracked" : ""}
          </p>
        </div>
      )}
      renderDetail={(item) => {
        if (creating) {
          return (
            <ItemCreateForm
              incomeOptions={incomeOptions.map((a) => ({
                id: a.id,
                label: `${a.code} ${a.name}`,
              }))}
              loadingAccounts={accounts.isPending}
              pending={create.isPending}
              error={create.error ? "Could not create item. Check fields and account." : null}
              onCancel={() => setCreating(false)}
              onSubmit={(body) => create.mutate(body)}
            />
          );
        }
        if (!item) {
          return (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <p className="text-base font-medium">Select an item</p>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground text-pretty">
                Choose a row to preview details, or create a new item.
              </p>
            </div>
          );
        }
        return (
          <div className="mx-auto w-full max-w-lg space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Item</p>
              <h2 className="text-xl font-semibold tracking-tight">{item.name}</h2>
            </div>
            <dl className="grid gap-3 text-sm">
              <PreviewField label="SKU" value={item.sku} mono />
              <PreviewField label="Kind" value={item.kind} />
              <PreviewField label="Unit price" value={item.unit_price} mono />
              <PreviewField label="Tracked" value={item.tracked ? "Yes" : "No"} />
              <PreviewField label="Income account" value={item.income_account_id} mono />
              <PreviewField label="Expense account" value={item.expense_account_id ?? "—"} mono />
            </dl>
            <p className="text-xs text-muted-foreground">
              Edit and delete will arrive when the API adds update routes.
            </p>
          </div>
        );
      }}
    />
  );
}

function PreviewField({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="grid gap-0.5 border-b border-border/60 pb-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={mono ? "font-mono text-sm break-all" : "text-sm"}>{value}</dd>
    </div>
  );
}

function ItemCreateForm({
  incomeOptions,
  loadingAccounts,
  pending,
  error,
  onCancel,
  onSubmit,
}: {
  incomeOptions: { id: string; label: string }[];
  loadingAccounts: boolean;
  pending: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (body: {
    sku: string;
    name: string;
    kind: string;
    tracked: boolean;
    unit_price: string;
    income_account_id: string;
  }) => void;
}) {
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState("good");
  const [tracked, setTracked] = useState(true);
  const [unitPrice, setUnitPrice] = useState("0");
  const [incomeAccountId, setIncomeAccountId] = useState("");

  return (
    <form
      className="mx-auto w-full max-w-md"
      onSubmit={(e) => {
        e.preventDefault();
        if (!sku.trim() || !name.trim() || !incomeAccountId) return;
        onSubmit({
          sku: sku.trim(),
          name: name.trim(),
          kind,
          tracked,
          unit_price: unitPrice || "0",
          income_account_id: incomeAccountId,
        });
      }}
    >
      <FieldGroup>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">New item</h2>
        </div>

        <Field>
          <FieldLabel htmlFor="item-sku">SKU</FieldLabel>
          <Input id="item-sku" value={sku} onChange={(e) => setSku(e.target.value)} required />
        </Field>

        <Field>
          <FieldLabel htmlFor="item-name">Name</FieldLabel>
          <Input id="item-name" value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>

        <Field>
          <FieldLabel>Kind</FieldLabel>
          <Select value={kind} onValueChange={(v) => setKind(String(v ?? "good"))}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="good">Good</SelectItem>
              <SelectItem value="service">Service</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        <Field>
          <FieldLabel htmlFor="item-price">Unit price</FieldLabel>
          <Input
            id="item-price"
            value={unitPrice}
            onChange={(e) => setUnitPrice(e.target.value)}
            className="font-mono"
          />
        </Field>

        <Field orientation="horizontal" className="items-center">
          <Checkbox
            id="item-tracked"
            checked={tracked}
            onCheckedChange={(v) => setTracked(v === true)}
          />
          <FieldLabel htmlFor="item-tracked" className="font-normal">
            Track stock
          </FieldLabel>
        </Field>

        <Field>
          <FieldLabel>Income account</FieldLabel>
          <Select
            value={incomeAccountId || undefined}
            onValueChange={(v) => setIncomeAccountId(String(v ?? ""))}
            disabled={loadingAccounts}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={loadingAccounts ? "Loading…" : "Select account"} />
            </SelectTrigger>
            <SelectContent>
              {incomeOptions.map((a) => (
                <SelectItem key={a.id} value={a.id}>
                  {a.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>

        {error ? <FieldError>{error}</FieldError> : null}

        <div className="flex gap-2">
          <Button type="submit" disabled={pending || !incomeAccountId}>
            {pending ? "Saving…" : "Create"}
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </FieldGroup>
    </form>
  );
}
