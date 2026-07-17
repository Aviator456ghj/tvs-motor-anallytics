"use client";

import { ShoppingCart, ShoppingBag, Users, Filter, BarChart3, DollarSign, ArrowUp, ArrowDown, type LucideIcon } from "lucide-react";
import { Line, LineChart, ResponsiveContainer } from "recharts";
import { Card } from "@/components/ui/Card";
import { statCards, type StatCard } from "@/lib/dashboard-data";

const iconMap: Record<StatCard["icon"], LucideIcon> = {
  cart: ShoppingCart,
  bag: ShoppingBag,
  users: Users,
  filter: Filter,
  chart: BarChart3,
  dollar: DollarSign,
};

export default function StatCardsRow() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
      {statCards.map((stat) => {
        const Icon = iconMap[stat.icon];
        const DeltaIcon = stat.deltaDirection === "up" ? ArrowUp : ArrowDown;
        const data = stat.sparkline.map((v, i) => ({ i, v }));
        return (
          <Card key={stat.id} className="p-4 flex flex-col gap-3">
            <div className="flex items-start justify-between">
              <span className="text-[12.5px] font-medium text-muted">{stat.label}</span>
              <span className={`w-8 h-8 rounded-lg flex items-center justify-center ${stat.iconBg} ${stat.iconColor}`}>
                <Icon size={16} strokeWidth={2.2} />
              </span>
            </div>
            <div className="text-[22px] font-bold text-foreground leading-none tracking-tight">
              {stat.value}
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-0.5 text-[12px] font-semibold text-success">
                <DeltaIcon size={12} />
                {stat.delta}
              </span>
              <span className="text-[11px] text-muted-light">{stat.compareLabel}</span>
            </div>
            <div className="h-8 -mx-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke={stat.sparklineColor}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
