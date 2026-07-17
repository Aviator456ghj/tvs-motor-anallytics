"use client";

import { useState } from "react";
import { Download, MoreVertical, ChevronDown, Check } from "lucide-react";
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
import { salesOverviewByRange, salesRangeOptions, type SalesRange } from "@/lib/dashboard-data";

export default function SalesOverviewCard() {
  const [range, setRange] = useState<SalesRange>("Daily");
  const [menuOpen, setMenuOpen] = useState(false);
  const data = range === "Custom Range" ? salesOverviewByRange.Daily : salesOverviewByRange[range];

  return (
    <Card className="p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[14.5px] font-semibold text-foreground">Sales Overview</h3>
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="flex items-center gap-1 text-[12.5px] font-medium text-muted border border-card-border rounded-lg px-2.5 py-1.5 hover:bg-background/80"
            >
              {range} <ChevronDown size={13} />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 w-40 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                  {salesRangeOptions.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => {
                        setRange(opt);
                        setMenuOpen(false);
                      }}
                      className="w-full flex items-center justify-between gap-2 px-3 py-1.5 text-[12.5px] text-foreground hover:bg-background/80"
                    >
                      {opt}
                      {opt === range && <Check size={13} className="text-brand-start" />}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
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
        {range === "Custom Range" && (
          <span className="text-[11.5px] text-muted-light ml-auto">Showing Daily as a preview — pick exact dates soon</span>
        )}
      </div>

      <div className="h-[230px] -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="#eef0f5" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tickFormatter={(v) => (v >= 1000 ? `$${Math.round(v / 1000)}K` : `$${v}`)}
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
