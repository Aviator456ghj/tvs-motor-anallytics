"use client";

import { useState } from "react";
import { ShoppingCart, DollarSign, BarChart3, Clock, RotateCcw, ArrowUp, ArrowDown, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { ordersKpis, type OrdersKpi } from "@/lib/orders-data";

const iconMap: Record<OrdersKpi["icon"], LucideIcon> = {
  cart: ShoppingCart,
  dollar: DollarSign,
  chart: BarChart3,
  clock: Clock,
  rotate: RotateCcw,
};

export default function OrdersKpiRow() {
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-4">
      {ordersKpis.map((kpi) => {
        const Icon = iconMap[kpi.icon];
        const DeltaIcon = kpi.direction === "up" ? ArrowUp : ArrowDown;
        const deltaColor = kpi.direction === "up" ? "text-success" : "text-danger";
        const open = openId === kpi.id;
        return (
          <Card key={kpi.id} className="p-4 flex flex-col gap-2.5 relative">
            <button
              onClick={() => setOpenId(open ? null : kpi.id)}
              className="flex items-start justify-between text-left w-full"
            >
              <span className="text-[12.5px] font-medium text-muted">{kpi.label}</span>
              <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${kpi.iconBg} ${kpi.iconColor}`}>
                <Icon size={16} strokeWidth={2.2} />
              </span>
            </button>
            <div className="text-[21px] font-bold text-foreground leading-none tracking-tight">{kpi.value}</div>
            <div className="flex items-center justify-between">
              <span className={`flex items-center gap-0.5 text-[12px] font-semibold ${deltaColor}`}>
                <DeltaIcon size={12} />
                {kpi.delta}
              </span>
              <span className="text-[11px] text-muted-light">{kpi.compareLabel}</span>
            </div>

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
