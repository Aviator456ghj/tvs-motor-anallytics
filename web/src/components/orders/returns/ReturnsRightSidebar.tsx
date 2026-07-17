"use client";

import { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { PlusSquare, ShieldCheck, Tag, FileText, ListChecks, Sparkles, X, TriangleAlert, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { returnsOverview, reasonsSummary, quickActions, aiInsights } from "@/lib/returns-data";

const iconMap: Record<string, LucideIcon> = {
  "plus-square": PlusSquare,
  "shield-check": ShieldCheck,
  tag: Tag,
  "file-text": FileText,
  "list-checks": ListChecks,
};

const toneStyle = { warning: "text-warning", danger: "text-danger", info: "text-info" };

const totalReturns = 98;

export default function ReturnsRightSidebar() {
  const [insightsOpen, setInsightsOpen] = useState(true);

  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Returns Overview</h3>
        <div className="relative h-[150px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={returnsOverview} dataKey="count" nameKey="label" innerRadius="66%" outerRadius="100%" paddingAngle={2} stroke="none" isAnimationActive={false}>
                {returnsOverview.map((p) => (
                  <Cell key={p.label} fill={p.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-[20px] font-bold text-foreground">{totalReturns}</span>
            <span className="text-[10.5px] text-muted-light">Total Returns</span>
          </div>
        </div>
        <div className="flex flex-col gap-1.5 mt-2">
          {returnsOverview.map((p) => (
            <div key={p.label} className="flex items-center gap-2 text-[11.5px]">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
              <span className="flex-1 text-muted truncate">{p.label}</span>
              <span className="text-foreground font-medium">
                {p.count} ({p.pct}%)
              </span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[13.5px] font-semibold text-foreground">Reasons Summary</h3>
          <button className="text-[11.5px] font-medium text-brand-start hover:underline">View All</button>
        </div>
        <div className="flex flex-col gap-3">
          {reasonsSummary.map((r) => (
            <div key={r.label}>
              <div className="flex items-center justify-between text-[12px] mb-1">
                <span className="text-foreground">{r.label}</span>
                <span className="text-muted-light">
                  {r.count} ({r.pct}%)
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-background overflow-hidden">
                <div className="h-full rounded-full bg-brand-start" style={{ width: `${r.pct}%` }} />
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Quick Actions</h3>
        <div className="flex flex-col gap-1">
          {quickActions.map((qa) => {
            const Icon = iconMap[qa.icon];
            return (
              <button key={qa.id} className="flex items-center gap-2.5 rounded-lg px-2 py-2 text-[12.5px] font-medium text-foreground hover:bg-background/80 text-left">
                <span className="w-7 h-7 rounded-lg bg-background flex items-center justify-center text-brand-start shrink-0">
                  <Icon size={14} />
                </span>
                {qa.label}
              </button>
            );
          })}
        </div>
      </Card>

      {insightsOpen && (
        <Card className="p-4 bg-gradient-to-br from-brand-start/[0.06] to-brand-end/[0.06] border-brand-start/20">
          <div className="flex items-center justify-between mb-2.5">
            <h3 className="text-[13.5px] font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles size={14} className="text-brand-start" /> AI Insights
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-brand-start/10 text-brand-start">Beta</span>
            </h3>
            <button onClick={() => setInsightsOpen(false)} className="text-muted-light hover:text-muted">
              <X size={14} />
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {aiInsights.map((insight) => (
              <div key={insight.id} className="flex items-center gap-2 text-[12px] text-foreground">
                <TriangleAlert size={13} className={`${toneStyle[insight.tone]} shrink-0`} />
                {insight.text}
              </div>
            ))}
          </div>
          <button className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline mt-2.5">View all insights →</button>
        </Card>
      )}
    </div>
  );
}
