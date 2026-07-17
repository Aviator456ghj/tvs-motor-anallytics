"use client";

import { useState } from "react";
import { Search, SlidersHorizontal, Settings2, Calendar, ChevronDown } from "lucide-react";
import { statusOptions, reasonOptions, warehouseOptions, returnTypeOptions, filterGroups } from "@/lib/returns-data";

export default function ReturnsToolbar({
  search,
  onSearchChange,
  status,
  onStatusChange,
  reason,
  onReasonChange,
  warehouse,
  onWarehouseChange,
  returnType,
  onReturnTypeChange,
}: {
  search: string;
  onSearchChange: (v: string) => void;
  status: string;
  onStatusChange: (v: string) => void;
  reason: string;
  onReasonChange: (v: string) => void;
  warehouse: string;
  onWarehouseChange: (v: string) => void;
  returnType: string;
  onReturnTypeChange: (v: string) => void;
}) {
  const [filtersOpen, setFiltersOpen] = useState(false);

  return (
    <div className="flex flex-col gap-2.5">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-light" size={15} />
        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by RMA ID, Order ID, customer, SKU..."
          className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-card-border bg-background/60 text-[13px] placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30"
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Select label="Status" value={status} options={statusOptions} onChange={onStatusChange} />
        <Select label="Reason" value={reason} options={reasonOptions} onChange={onReasonChange} />
        <Select label="Warehouse" value={warehouse} options={warehouseOptions} onChange={onWarehouseChange} />
        <Select label="Return Type" value={returnType} options={returnTypeOptions} onChange={onReturnTypeChange} />
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] text-muted-light px-0.5">Requested Date</label>
          <button className="flex items-center gap-1.5 rounded-lg border border-card-border bg-card-bg text-[12.5px] px-2.5 py-1.5 text-muted">
            <Calendar size={12} /> Select date range
          </button>
        </div>

        <div className="relative ml-auto flex items-center gap-1.5">
          <button
            onClick={() => setFiltersOpen((v) => !v)}
            className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80"
          >
            <SlidersHorizontal size={13} />
            Filters
          </button>
          <button className="w-8 h-8 flex items-center justify-center rounded-lg border border-card-border bg-card-bg text-muted hover:bg-background/80" title="Table settings">
            <Settings2 size={14} />
          </button>
          {filtersOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setFiltersOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-56 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
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
      </div>
    </div>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-[10px] text-muted-light px-0.5">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-card-border bg-card-bg text-[12.5px] px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-start/30"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
