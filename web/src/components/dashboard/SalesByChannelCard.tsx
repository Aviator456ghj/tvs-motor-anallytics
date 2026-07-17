"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { Card } from "@/components/ui/Card";
import { salesByChannel } from "@/lib/dashboard-data";

const total = "$24,560.90";

export default function SalesByChannelCard() {
  return (
    <Card className="p-5 flex flex-col gap-3">
      <h3 className="text-[14.5px] font-semibold text-foreground">Sales by Channel</h3>

      <div className="h-[150px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={salesByChannel}
              dataKey="pct"
              nameKey="channel"
              innerRadius="68%"
              outerRadius="100%"
              paddingAngle={2}
              stroke="none"
              isAnimationActive={false}
            >
              {salesByChannel.map((c) => (
                <Cell key={c.channel} fill={c.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-col gap-2">
        {salesByChannel.map((c) => (
          <div key={c.channel} className="flex items-center gap-2 text-[12.5px]">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: c.color }} />
            <span className="flex-1 text-muted truncate">{c.channel}</span>
            <span className="text-muted-light w-11 text-right shrink-0">{c.pct}%</span>
            <span className="font-medium text-foreground w-20 text-right shrink-0">{c.amount}</span>
          </div>
        ))}
        <div className="flex items-center justify-between pt-2 mt-1 border-t border-card-border text-[13px]">
          <span className="font-semibold text-foreground">Total</span>
          <span className="font-semibold text-foreground">{total}</span>
        </div>
      </div>
    </Card>
  );
}
