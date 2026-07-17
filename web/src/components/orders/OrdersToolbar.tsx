"use client";

import { useState } from "react";
import { Search, SlidersHorizontal, Columns3, ArrowUpDown, ChevronDown, Check } from "lucide-react";
import { filterGroups, sortOptions, orderColumns, bulkActions, type OrderColumnKey, type BulkActionKey } from "@/lib/orders-data";

export default function OrdersToolbar({
  search,
  onSearchChange,
  visibleColumns,
  onToggleColumn,
  sort,
  onSortChange,
  selectedCount,
  onBulkAction,
}: {
  search: string;
  onSearchChange: (v: string) => void;
  visibleColumns: Set<OrderColumnKey>;
  onToggleColumn: (key: OrderColumnKey) => void;
  sort: string;
  onSortChange: (v: string) => void;
  selectedCount: number;
  onBulkAction: (key: BulkActionKey) => void;
}) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [sortOpen, setSortOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);

  return (
    <div className="flex flex-col md:flex-row md:items-center gap-2">
      <div className="relative flex-1 min-w-0">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-light" size={15} />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search orders by number, customer, email, product..."
          className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-card-border bg-card-bg text-[13px] placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30 focus:border-brand-start/50"
        />
      </div>

      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        <div className="relative">
          <button
            onClick={() => setFiltersOpen((v) => !v)}
            className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2.5 bg-card-bg hover:bg-background/80"
          >
            <SlidersHorizontal size={14} />
            Filters
          </button>
          {filtersOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setFiltersOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-56 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1 max-h-80 overflow-y-auto">
                {filterGroups.map((g) => (
                  <button key={g} className="w-full flex items-center justify-between px-3 py-2 text-[12.5px] text-foreground hover:bg-background/80">
                    {g}
                    <ChevronDown size={13} className="text-muted-light -rotate-90" />
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => setColumnsOpen((v) => !v)}
            className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2.5 bg-card-bg hover:bg-background/80"
          >
            <Columns3 size={14} />
            Columns
          </button>
          {columnsOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setColumnsOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-52 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1 max-h-80 overflow-y-auto">
                {orderColumns.map((c) => (
                  <button
                    key={c.key}
                    onClick={() => onToggleColumn(c.key)}
                    className="w-full flex items-center justify-between px-3 py-2 text-[12.5px] text-foreground hover:bg-background/80"
                  >
                    {c.label}
                    {visibleColumns.has(c.key) && <Check size={13} className="text-brand-start" />}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => setSortOpen((v) => !v)}
            className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2.5 bg-card-bg hover:bg-background/80"
          >
            <ArrowUpDown size={14} />
            Sort: {sort}
            <ChevronDown size={13} />
          </button>
          {sortOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setSortOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-52 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                {sortOptions.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      onSortChange(s);
                      setSortOpen(false);
                    }}
                    className="w-full flex items-center justify-between px-3 py-2 text-[12.5px] text-foreground hover:bg-background/80"
                  >
                    {s}
                    {s === sort && <Check size={13} className="text-brand-start" />}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => setBulkOpen((v) => !v)}
            disabled={selectedCount === 0}
            className="flex items-center gap-1.5 text-[13px] font-medium rounded-lg px-3 py-2.5 border border-card-border bg-card-bg text-foreground hover:bg-background/80 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Bulk actions {selectedCount > 0 && `(${selectedCount})`}
            <ChevronDown size={13} />
          </button>
          {bulkOpen && selectedCount > 0 && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setBulkOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-48 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1 max-h-80 overflow-y-auto">
                {bulkActions.map((a) => (
                  <button
                    key={a.key}
                    onClick={() => {
                      onBulkAction(a.key);
                      setBulkOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-[12.5px] hover:bg-background/80 ${a.danger ? "text-danger" : "text-foreground"}`}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
