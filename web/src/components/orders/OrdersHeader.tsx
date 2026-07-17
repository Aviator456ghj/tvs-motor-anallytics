"use client";

import { ChevronRight, Download, Upload, ChevronDown, Plus } from "lucide-react";

export default function OrdersHeader() {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <div className="flex items-center gap-1.5 text-[12.5px] text-muted-light mb-1">
          <span>Dashboard</span>
          <ChevronRight size={13} />
          <span className="text-foreground font-medium">Orders</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Orders</h1>
      </div>
      <div className="flex items-center gap-2">
        <button className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80">
          <Download size={14} />
          Export
        </button>
        <button className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80">
          <Upload size={14} />
          Import
        </button>
        <button className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white text-[13px] font-medium pl-4 pr-3 py-2 shadow-sm hover:opacity-90 transition-opacity">
          <Plus size={14} />
          Create Order
          <ChevronDown size={13} className="ml-1" />
        </button>
      </div>
    </div>
  );
}
