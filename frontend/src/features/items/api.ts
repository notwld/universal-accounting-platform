import { api } from "@/lib/api/client";
import type { ApiData } from "@/types/api";

export type FinanceItem = {
  id: string;
  sku: string;
  name: string;
  kind: string;
  tracked: boolean;
  unit_price: string;
  income_account_id: string;
  expense_account_id: string | null;
};

export type Warehouse = { id: string; name: string };

export type StockBalance = {
  item_id: string;
  warehouse_id: string;
  qty: string;
  value: string;
};

export type AccountOption = {
  id: string;
  code: string;
  name: string;
  classification: string;
};

export async function listItems() {
  const { data } = await api.get<ApiData<{ items: FinanceItem[] }>>("/finance/items");
  return data.data.items;
}

export async function createItem(body: {
  sku: string;
  name: string;
  kind?: string;
  tracked?: boolean;
  unit_price?: string;
  income_account_id: string;
  expense_account_id?: string | null;
}) {
  const { data } = await api.post<ApiData<FinanceItem>>("/finance/items", body);
  return data.data;
}

export async function listWarehouses() {
  const { data } = await api.get<ApiData<{ items: Warehouse[] }>>("/finance/warehouses");
  return data.data.items;
}

export async function createWarehouse(name: string) {
  const { data } = await api.post<ApiData<Warehouse>>("/finance/warehouses", { name });
  return data.data;
}

export async function listStockBalances() {
  const { data } = await api.get<ApiData<{ items: StockBalance[] }>>("/finance/stock/balances");
  return data.data.items;
}

export async function adjustStock(body: {
  warehouse_id: string;
  item_id: string;
  quantity: string;
  unit_cost?: string;
  entry_date?: string;
}) {
  const { data } = await api.post<ApiData<{ journal_id: string; item_id: string; warehouse_id: string }>>(
    "/finance/stock/adjust",
    body,
    { headers: { "Idempotency-Key": crypto.randomUUID() } }
  );
  return data.data;
}

export async function transferStock(body: {
  from_warehouse_id: string;
  to_warehouse_id: string;
  item_id: string;
  quantity: string;
  entry_date?: string;
}) {
  const { data } = await api.post<
    ApiData<{ from_warehouse_id: string; to_warehouse_id: string; item_id: string }>
  >("/finance/stock/transfer", body);
  return data.data;
}

export async function listAccounts() {
  const { data } = await api.get<ApiData<{ items: AccountOption[] }>>("/finance/accounts");
  return data.data.items;
}
