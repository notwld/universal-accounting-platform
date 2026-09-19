"use client";

import { ChevronLeft, ChevronRight, Settings2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200] as const;

type PageSizePaginationProps = {
  page: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  rangeStart: number;
  rangeEnd: number;
  pageSizeOptions?: readonly number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  className?: string;
};

/**
 * Compact footer control: searchable page-size popover + prev / range / next.
 * Pattern: Elastic table pagination + shadcn Combobox (Popover + Command).
 */
export function PageSizePagination({
  page,
  totalPages,
  pageSize,
  totalItems,
  rangeStart,
  rangeEnd,
  pageSizeOptions = PAGE_SIZE_OPTIONS,
  onPageChange,
  onPageSizeChange,
  className,
}: PageSizePaginationProps) {
  const [open, setOpen] = useState(false);

  return (
    <div
      role="navigation"
      aria-label="Pagination"
      className={cn(
        "flex h-9 w-full items-stretch overflow-hidden rounded-lg border border-border bg-background text-xs shadow-xs",
        className
      )}
    >
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-auto flex-1 justify-start gap-1.5 rounded-none border-0 bg-muted/50 px-2.5 font-normal hover:bg-muted"
            />
          }
        >
          <Settings2 className="size-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate tabular-nums">
            {pageSize} per page
          </span>
        </PopoverTrigger>
        <PopoverContent align="start" side="top" className="w-52 p-0">
          <Command>
            <CommandInput placeholder="Search" />
            <CommandList>
              <CommandEmpty>No size found.</CommandEmpty>
              <CommandGroup>
                {pageSizeOptions.map((n) => {
                  const selected = n === pageSize;
                  return (
                    <CommandItem
                      key={n}
                      value={`${n} per page`}
                      data-checked={selected ? "true" : undefined}
                      onSelect={() => {
                        onPageSizeChange(n);
                        setOpen(false);
                      }}
                      className={cn(
                        selected && "bg-muted",
                        "data-selected:bg-[oklch(0.55_0.14_250)] data-selected:text-white"
                      )}
                    >
                      <span className="flex-1 tabular-nums">{n} per page</span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <Separator orientation="vertical" className="h-auto self-stretch" />

      <div className="flex shrink-0 items-center">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="h-full rounded-none px-2"
          disabled={page <= 1}
          aria-label="Previous page"
          onClick={() => onPageChange(Math.max(1, page - 1))}
        >
          <ChevronLeft
            className={cn(
              "size-4",
              page <= 1 ? "text-muted-foreground" : "text-[oklch(0.55_0.14_250)]"
            )}
          />
        </Button>
        <span className="min-w-14 px-1 text-center tabular-nums text-muted-foreground">
          {totalItems === 0 ? "0" : `${rangeStart} - ${rangeEnd}`}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="h-full rounded-none px-2"
          disabled={page >= totalPages}
          aria-label="Next page"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        >
          <ChevronRight
            className={cn(
              "size-4",
              page >= totalPages
                ? "text-muted-foreground"
                : "text-[oklch(0.55_0.14_250)]"
            )}
          />
        </Button>
      </div>
    </div>
  );
}
