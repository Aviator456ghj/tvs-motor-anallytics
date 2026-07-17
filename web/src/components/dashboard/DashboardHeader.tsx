"use client";

import { SlidersHorizontal, MoreVertical, Calendar } from "lucide-react";

export default function DashboardHeader() {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Dashboard</h1>
        <p className="text-[13px] text-muted-light mt-0.5">Here&apos;s what&apos;s happening with your store today.</p>
      </div>
      <div className="flex items-center gap-2">
        <button className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80">
          <SlidersHorizontal size={14} />
          Customize
        </button>
        <button className="w-9 h-9 flex items-center justify-center rounded-lg border border-card-border bg-card-bg text-muted hover:bg-background/80">
          <MoreVertical size={15} />
        </button>
        <button className="flex items-center gap-2 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80">
          <Calendar size={14} />
          May 10 – May 16, 2025
        </button>
      </div>
    </div>
  );
}
