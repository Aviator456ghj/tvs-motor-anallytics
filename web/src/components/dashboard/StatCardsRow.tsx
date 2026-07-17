"use client";

import {
  ShoppingCart,
  ShoppingBag,
  Users,
  Filter,
  BarChart3,
  DollarSign,
  Calendar,
  TrendingUp,
  Clock,
  Repeat,
  Package,
  RotateCcw,
  AlertTriangle,
  ArrowUp,
  ArrowDown,
  type LucideIcon,
} from "lucide-react";
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
  calendar: Calendar,
  "trending-up": TrendingUp,
  clock: Clock,
  repeat: Repeat,
  package: Package,
  "rotate-ccw": RotateCcw,
  "alert-triangle": AlertTriangle,
};

export default function StatCardsRow() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
      {statCards.map((stat) => {
        const Icon = iconMap[stat.icon];
        const DeltaIcon = stat.deltaDirection === "up" ? ArrowUp : ArrowDown;
        const deltaColor = stat.deltaDirection === "up" ? "text-success" : "text-danger";
        const data = stat.sparkline.map((v, i) => ({ i, v }));
        return (
          <Card key={stat.id} className="p-3.5 flex flex-col gap-2.5">
            <div className="flex items-start justify-between">
              <span className="text-[11.5px] font-medium text-muted leading-tight">{stat.label}</span>
              <span className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${stat.iconBg} ${stat.iconColor}`}>
                <Icon size={14} strokeWidth={2.2} />
              </span>
            </div>
            <div className="text-[19px] font-bold text-foreground leading-none tracking-tight">
              {stat.value}
            </div>
            <div className="flex items-center justify-between gap-1">
              <span className={`flex items-center gap-0.5 text-[11px] font-semibold shrink-0 ${deltaColor}`}>
                <DeltaIcon size={11} />
                {stat.delta}
              </span>
              <span className="text-[10.5px] text-muted-light truncate text-right">{stat.compareLabel}</span>
            </div>
            <div className="h-6 -mx-1">
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
