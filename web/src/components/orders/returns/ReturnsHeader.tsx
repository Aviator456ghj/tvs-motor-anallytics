"use client";

import { useState } from "react";
import { ChevronRight, Download, Printer, ChevronDown, Plus } from "lucide-react";

export default function ReturnsHeader() {
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <div className="flex items-center gap-1.5 text-[12.5px] text-muted-light mb-1">
          <span>Dashboard</span>
          <ChevronRight size={13} />
          <span>Orders</span>
          <ChevronRight size={13} />
          <span className="text-foreground font-medium">Returns (RMA)</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Returns (RMA)</h1>
      </div>
      <div className="flex items-center gap-2">
        <button className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80">
          <Download size={14} />
          Export
        </button>
        <button className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80">
          <Printer size={14} />
          Print RMA List
        </button>
        <div className="relative">
          <button
            onClick={() => setCreateOpen((v) => !v)}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white text-[13px] font-medium pl-4 pr-3 py-2 shadow-sm hover:opacity-90 transition-opacity"
          >
            <Plus size={14} />
            Create RMA
            <ChevronDown size={13} className="ml-0.5" />
          </button>
          {createOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setCreateOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-48 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                {["From existing order", "Manual RMA", "Bulk RMA import"].map((opt) => (
                  <button key={opt} onClick={() => setCreateOpen(false)} className="w-full text-left px-3 py-2 text-[12.5px] text-foreground hover:bg-background/80">
                    {opt}
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
