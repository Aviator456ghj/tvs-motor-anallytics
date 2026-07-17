"use client";

import { statusTabs, type FulfillmentBucket } from "@/lib/fulfillment-data";

export default function FulfillmentTabs({ active, onChange }: { active: FulfillmentBucket; onChange: (key: FulfillmentBucket) => void }) {
  return (
    <div className="flex items-center gap-5 overflow-x-auto border-b border-card-border px-1">
      {statusTabs.map((tab) => {
        const isActive = tab.key === active;
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`flex items-center gap-1.5 text-[13px] font-medium whitespace-nowrap pb-3 pt-1 border-b-2 -mb-px transition-colors ${
              isActive ? "border-brand-start text-brand-start" : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {tab.label}
            <span className={`text-[11px] ${isActive ? "text-brand-start" : "text-muted-light"}`}>({tab.count})</span>
          </button>
        );
      })}
    </div>
  );
}
