"use client";

import { Search, Sparkles, Share2, MessageSquare, Bell, HelpCircle, ChevronDown } from "lucide-react";

export default function Topbar() {
  return (
    <header className="sticky top-0 z-20 h-16 shrink-0 flex items-center justify-between gap-4 px-6 bg-card-bg border-b border-card-border">
      <div className="relative w-full max-w-[360px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-light" size={16} />
        <input
          type="text"
          placeholder="Search anything..."
          className="w-full pl-9 pr-14 py-2 rounded-lg border border-card-border bg-background/60 text-sm placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30 focus:border-brand-start/50"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-medium text-muted-light border border-card-border rounded px-1.5 py-0.5">
          ⌘K
        </span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white text-[13px] font-medium px-4 py-2 shadow-sm hover:opacity-90 transition-opacity">
          <Sparkles size={15} />
          Ask AI Assistant
        </button>

        <IconButton icon={Share2} />
        <IconButton icon={MessageSquare} badge={8} badgeColor="bg-red-500" />
        <IconButton icon={Bell} badge={6} badgeColor="bg-red-500" />
        <IconButton icon={HelpCircle} />

        <button className="flex items-center gap-2.5 pl-2 pr-1 py-1 rounded-lg hover:bg-background/80 transition-colors">
          <span className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-start to-brand-end flex items-center justify-center text-white text-[12px] font-semibold shrink-0">
            JD
          </span>
          <div className="text-left leading-tight hidden sm:block">
            <div className="text-[13px] font-semibold text-foreground">John Doe</div>
            <div className="text-[11px] text-muted-light">Owner</div>
          </div>
          <ChevronDown size={14} className="text-muted-light hidden sm:block" />
        </button>
      </div>
    </header>
  );
}

function IconButton({
  icon: Icon,
  badge,
  badgeColor = "bg-red-500",
}: {
  icon: typeof Bell;
  badge?: number;
  badgeColor?: string;
}) {
  return (
    <button className="relative w-9 h-9 flex items-center justify-center rounded-lg text-muted hover:bg-background/80 transition-colors">
      <Icon size={17} />
      {badge !== undefined && (
        <span
          className={`absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full ${badgeColor} text-white text-[10px] font-semibold flex items-center justify-center`}
        >
          {badge}
        </span>
      )}
    </button>
  );
}
