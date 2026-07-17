"use client";

import { useState } from "react";
import {
  Pencil,
  Copy,
  Receipt,
  FileText,
  Mail,
  StickyNote,
  XCircle,
  Sparkles,
  X,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { orderDetail, quickActions } from "@/lib/order-detail-data";

const iconMap: Record<string, LucideIcon> = {
  pencil: Pencil,
  copy: Copy,
  receipt: Receipt,
  "file-text": FileText,
  mail: Mail,
  "sticky-note": StickyNote,
  "x-circle": XCircle,
};

export default function OrderDetailSidebar() {
  const [insightsOpen, setInsightsOpen] = useState(true);
  const o = orderDetail;

  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Quick Actions</h3>
        <div className="flex flex-col gap-1">
          {quickActions.map((qa) => {
            const Icon = iconMap[qa.icon];
            const danger = "danger" in qa && qa.danger;
            return (
              <button
                key={qa.key}
                className={`flex items-center gap-2.5 rounded-lg px-2 py-2 text-[12.5px] font-medium text-left hover:bg-background/80 ${
                  danger ? "text-danger" : "text-foreground"
                }`}
              >
                <span className={`w-7 h-7 rounded-lg bg-background flex items-center justify-center shrink-0 ${danger ? "text-danger" : "text-brand-start"}`}>
                  <Icon size={14} />
                </span>
                {qa.label}
              </button>
            );
          })}
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[13.5px] font-semibold text-foreground">Order Notes ({o.notes.length})</h3>
          <button className="text-[12px] font-medium text-brand-start hover:underline">Add Note</button>
        </div>
        <div className="flex flex-col gap-2.5">
          {o.notes.map((n) => (
            <div key={n.id} className={`rounded-lg p-3 ${n.type === "customer" ? "bg-warning-bg" : "bg-background"}`}>
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-semibold text-foreground">{n.title}</span>
                <span className="text-[10.5px] text-muted-light">{n.time}</span>
              </div>
              <p className="text-[11.5px] text-foreground mt-1 leading-snug">{n.body}</p>
              <div className="text-[10.5px] text-muted-light mt-1">Added by {n.author}</div>
            </div>
          ))}
        </div>
        <button className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline mt-2.5">
          View all notes <ChevronRight size={12} />
        </button>
      </Card>

      {insightsOpen && (
        <Card className="p-4 bg-gradient-to-br from-brand-start/[0.06] to-brand-end/[0.06] border-brand-start/20">
          <div className="flex items-center justify-between mb-2.5">
            <h3 className="text-[13.5px] font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles size={14} className="text-brand-start" /> AI Insights
            </h3>
            <button onClick={() => setInsightsOpen(false)} className="text-muted-light hover:text-muted">
              <X size={14} />
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {o.aiInsights.map((insight) => (
              <div key={insight.id} className="flex items-center gap-2 text-[12px] text-foreground">
                {insight.tone === "success" ? (
                  <CheckCircle2 size={13} className="text-success shrink-0" />
                ) : (
                  <AlertTriangle size={13} className="text-warning shrink-0" />
                )}
                {insight.text}
              </div>
            ))}
          </div>
          <button className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline mt-2.5">
            View all insights <ChevronRight size={12} />
          </button>
        </Card>
      )}
    </div>
  );
}
