"use client";

import { useState } from "react";
import { ShoppingBag, ShieldCheck, Shuffle, PackageOpen, Wallet, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { returnsKpis, type ReturnsKpi } from "@/lib/returns-data";

const iconMap: Record<ReturnsKpi["icon"], LucideIcon> = {
  "shopping-bag": ShoppingBag,
  "shield-check": ShieldCheck,
  shuffle: Shuffle,
  "package-open": PackageOpen,
  wallet: Wallet,
};

export default function ReturnsKpiRow() {
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-4">
      {returnsKpis.map((kpi) => {
        const Icon = iconMap[kpi.icon];
        const open = openId === kpi.id;
        return (
          <Card key={kpi.id} className="p-4 flex flex-col gap-2.5 relative">
            <button onClick={() => setOpenId(open ? null : kpi.id)} className="flex items-start gap-3 text-left w-full">
              <span className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${kpi.iconBg} ${kpi.iconColor}`}>
                <Icon size={17} strokeWidth={2.2} />
              </span>
              <span className="min-w-0">
                <div className="text-[12.5px] text-muted truncate">{kpi.label}</div>
                <div className="text-[19px] font-bold text-foreground leading-tight">{kpi.value}</div>
                <div className="text-[11px] text-muted-light truncate">{kpi.sub}</div>
              </span>
            </button>

            {open && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setOpenId(null)} />
                <div className="absolute left-0 right-0 top-full mt-1 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 p-3 flex flex-col gap-1.5">
                  {kpi.breakdown.map((b) => (
                    <div key={b.label} className="flex items-center justify-between text-[12px]">
                      <span className="text-muted">{b.label}</span>
                      <span className="font-medium text-foreground">{b.value}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        );
      })}
    </div>
  );
}
