"use client";

import { ListFilter, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import {
  PAGE_SIZE_OPTIONS,
  PageSizePagination,
} from "@/features/workspace/page-size-pagination";
import { cn } from "@/lib/utils";

export type FilterField = {
  key: string;
  label: string;
  options: { value: string; label: string }[];
};

type MasterDetailWorkspaceProps<T> = {
  title: string;
  subtitle?: string;
  items: T[];
  getId: (item: T) => string;
  searchPlaceholder?: string;
  searchText: (item: T) => string;
  filterFields?: FilterField[];
  matchFilters?: (item: T, filters: Record<string, string>) => boolean;
  renderRow: (item: T, selected: boolean) => React.ReactNode;
  renderDetail: (item: T | null, ctx: { clearSelection: () => void }) => React.ReactNode;
  toolbar?: React.ReactNode;
  loading?: boolean;
  error?: string | null;
  emptyLabel?: string;
  pageSizeOptions?: readonly number[];
  defaultPageSize?: number;
  className?: string;
};

export function MasterDetailWorkspace<T>({
  title,
  subtitle,
  items,
  getId,
  searchPlaceholder = "Search…",
  searchText,
  filterFields = [],
  matchFilters,
  renderRow,
  renderDetail,
  toolbar,
  loading,
  error,
  emptyLabel = "No records yet.",
  pageSizeOptions = PAGE_SIZE_OPTIONS,
  defaultPageSize = 25,
  className,
}: MasterDetailWorkspaceProps<T>) {
  const [query, setQuery] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [mobileShowDetail, setMobileShowDetail] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((item) => {
      if (q && !searchText(item).toLowerCase().includes(q)) return false;
      if (matchFilters) return matchFilters(item, filters);
      for (const [key, value] of Object.entries(filters)) {
        if (!value) continue;
        if (String((item as Record<string, unknown>)[key] ?? "") !== value) return false;
      }
      return true;
    });
  }, [items, query, filters, searchText, matchFilters]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize) || 1);
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * pageSize;
  const pageItems = filtered.slice(start, start + pageSize);
  const selected = items.find((i) => getId(i) === selectedId) ?? null;
  const activeFilterCount = Object.values(filters).filter(Boolean).length;
  const rangeStart = filtered.length === 0 ? 0 : start + 1;
  const rangeEnd = Math.min(start + pageSize, filtered.length);

  function select(id: string) {
    setSelectedId(id);
    setMobileShowDetail(true);
  }

  function clearSelection() {
    setSelectedId(null);
    setMobileShowDetail(false);
  }

  return (
    <div className={cn("flex h-full min-h-0 flex-col overflow-hidden", className)}>
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <section
          className={cn(
            "flex w-full min-h-0 flex-col border-border bg-[oklch(0.985_0.002_255)] lg:w-[22rem] lg:shrink-0 lg:border-r xl:w-96",
            mobileShowDetail ? "hidden lg:flex" : "flex"
          )}
        >
          <header className="shrink-0 space-y-3 border-b px-3 py-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h1 className="truncate text-base font-semibold tracking-tight">{title}</h1>
                {subtitle ? (
                  <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
                ) : null}
              </div>
              {toolbar}
            </div>

            <div className="flex items-center gap-1.5">
              <InputGroup className="min-w-0 flex-1 bg-background">
                <InputGroupAddon>
                  <Search className="text-muted-foreground" />
                </InputGroupAddon>
                <InputGroupInput
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setPage(1);
                  }}
                  placeholder={searchPlaceholder}
                  aria-label="Search list"
                />
              </InputGroup>
              {filterFields.length > 0 ? (
                <Button
                  type="button"
                  size="icon-sm"
                  variant={filtersOpen || activeFilterCount ? "secondary" : "outline"}
                  aria-label="Filters"
                  aria-expanded={filtersOpen}
                  aria-pressed={activeFilterCount > 0}
                  className="relative shrink-0"
                  onClick={() => setFiltersOpen((o) => !o)}
                >
                  <ListFilter />
                  {activeFilterCount > 0 ? (
                    <span className="absolute -top-1 -right-1 flex size-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground">
                      {activeFilterCount}
                    </span>
                  ) : null}
                </Button>
              ) : null}
            </div>

            {filtersOpen && filterFields.length > 0 ? (
              <div className="space-y-3 rounded-lg border bg-background p-2.5">
                {filterFields.map((field) => (
                  <Field key={field.key}>
                    <FieldLabel>{field.label}</FieldLabel>
                    <Select
                      value={filters[field.key] || "__all__"}
                      onValueChange={(value) => {
                        const next = value === "__all__" || value == null ? "" : String(value);
                        setFilters((f) => ({ ...f, [field.key]: next }));
                        setPage(1);
                      }}
                    >
                      <SelectTrigger size="sm" className="w-full">
                        <SelectValue>
                          {filters[field.key]
                            ? (field.options.find((o) => o.value === filters[field.key])?.label ??
                              filters[field.key])
                            : "All"}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__all__">All</SelectItem>
                        {field.options.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                ))}
                {activeFilterCount > 0 ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 w-full"
                    onClick={() => {
                      setFilters({});
                      setPage(1);
                    }}
                  >
                    Clear filters
                  </Button>
                ) : null}
              </div>
            ) : null}
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1.5 py-1.5">
            {loading ? (
              <Spinner className="min-h-32" />
            ) : error ? (
              <p className="px-2 py-6 text-center text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : pageItems.length === 0 ? (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">{emptyLabel}</p>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {pageItems.map((item) => {
                  const id = getId(item);
                  const selectedRow = id === selectedId;
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        onClick={() => select(id)}
                        className={cn(
                          "w-full rounded-md px-2.5 py-2.5 text-left transition-colors duration-150",
                          selectedRow
                            ? "bg-[oklch(0.55_0.14_250)] text-white"
                            : "hover:bg-black/[0.04]"
                        )}
                      >
                        {renderRow(item, selectedRow)}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <footer className="shrink-0 border-t p-2">
            <PageSizePagination
              page={safePage}
              totalPages={totalPages}
              pageSize={pageSize}
              totalItems={filtered.length}
              rangeStart={rangeStart}
              rangeEnd={rangeEnd}
              pageSizeOptions={pageSizeOptions}
              onPageChange={setPage}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setPage(1);
              }}
            />
          </footer>
        </section>

        <section
          className={cn(
            "min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain bg-background",
            mobileShowDetail ? "flex flex-col" : "hidden lg:flex lg:flex-col"
          )}
        >
          <div className="sticky top-0 z-10 flex items-center gap-2 border-b bg-background/95 px-3 py-2 backdrop-blur lg:hidden">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="gap-1"
              onClick={() => setMobileShowDetail(false)}
            >
              <X className="size-3.5" />
              List
            </Button>
          </div>
          <div className="flex flex-1 flex-col p-4 sm:p-6">
            {renderDetail(selected, { clearSelection })}
          </div>
        </section>
      </div>
    </div>
  );
}
