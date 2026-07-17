"use client";

import { Download, MoreVertical, ChevronDown } from "lucide-react";
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card } from "@/components/ui/Card";
import { salesOverview } from "@/lib/dashboard-data";

export default function SalesOverviewCard() {
  return (
    <Card className="p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[14.5px] font-semibold text-foreground">Sales Overview</h3>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1 text-[12.5px] font-medium text-muted border border-card-border rounded-lg px-2.5 py-1.5">
            Daily <ChevronDown size={13} />
          </button>
          <button className="w-7 h-7 flex items-center justify-center rounded-lg text-muted-light hover:bg-background/80">
            <Download size={14} />
          </button>
          <button className="w-7 h-7 flex items-center justify-center rounded-lg text-muted-light hover:bg-background/80">
            <MoreVertical size={14} />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4 text-[12.5px]">
        <span className="flex items-center gap-1.5 text-muted">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Sales
        </span>
        <span className="flex items-center gap-1.5 text-muted">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Orders
        </span>
      </div>

      <div className="h-[230px] -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={salesOverview} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="#eef0f5" />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tickFormatter={(v) => `$${v / 1000}K`}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 10,
                border: "1px solid #eaecf3",
                fontSize: 12,
              }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="sales"
              stroke="#3b82f6"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#3b82f6" }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="orders"
              stroke="#10b981"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#10b981" }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
