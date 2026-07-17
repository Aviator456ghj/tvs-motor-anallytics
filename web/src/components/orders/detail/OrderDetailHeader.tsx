"use client";

import { useState } from "react";
import { ChevronRight, ChevronLeft, ChevronDown, Printer, Mail, Calendar, Monitor, User, BadgeCheck } from "lucide-react";
import {
  orderDetail,
  moreActions,
  paymentStatusStyle,
  fulfillmentStatusStyle,
  orderStatusStyle,
} from "@/lib/order-detail-data";

export default function OrderDetailHeader() {
  const [moreOpen, setMoreOpen] = useState(false);
  const o = orderDetail;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2.5 mb-1">
            <h1 className="text-2xl font-bold text-foreground tracking-tight">Order {o.id}</h1>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${paymentStatusStyle[o.paymentStatus]}`}>{o.paymentStatus}</span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${fulfillmentStatusStyle.Processing}`}>{o.processingLabel}</span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${fulfillmentStatusStyle["Partially Fulfilled"]}`}>
              {o.fulfillmentStatus}
            </span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${orderStatusStyle[o.orderStatus]}`}>{o.orderStatus}</span>
          </div>
          <div className="flex items-center gap-1.5 text-[12.5px] text-muted-light">
            <span>Dashboard</span>
            <ChevronRight size={13} />
            <span>Orders</span>
            <ChevronRight size={13} />
            <span className="text-foreground font-medium">Order {o.id}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3.5 py-2 bg-card-bg hover:bg-background/80">
            <Printer size={14} /> Print
          </button>
          <button className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3.5 py-2 bg-card-bg hover:bg-background/80">
            <Mail size={14} /> Email
          </button>
          <div className="relative">
            <button
              onClick={() => setMoreOpen((v) => !v)}
              className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3.5 py-2 bg-card-bg hover:bg-background/80"
            >
              More Actions <ChevronDown size={13} />
            </button>
            {moreOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMoreOpen(false)} />
                <div className="absolute right-0 top-full mt-1 w-52 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1 max-h-96 overflow-y-auto">
                  {moreActions.map((a) => (
                    <button
                      key={a.key}
                      onClick={() => setMoreOpen(false)}
                      className={`w-full text-left px-3 py-2 text-[12.5px] hover:bg-background/80 ${"danger" in a && a.danger ? "text-danger" : "text-foreground"}`}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button className="w-9 h-9 flex items-center justify-center rounded-lg border border-card-border bg-card-bg text-muted hover:bg-background/80" title="Previous order">
              <ChevronLeft size={15} />
            </button>
            <button className="w-9 h-9 flex items-center justify-center rounded-lg border border-card-border bg-card-bg text-muted hover:bg-background/80" title="Next order">
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12.5px] text-muted">
        <span className="flex items-center gap-1.5">
          <Calendar size={13} className="text-muted-light" /> {o.placedAt}
        </span>
        <span className="text-card-border">|</span>
        <span className="flex items-center gap-1.5">
          <Monitor size={13} className="text-muted-light" /> {o.channel}
        </span>
        <span className="text-card-border">|</span>
        <span className="flex items-center gap-1.5">
          <User size={13} className="text-muted-light" /> {o.customer.name}
        </span>
        <span className="text-card-border">|</span>
        <span className="flex items-center gap-1.5">
          <BadgeCheck size={13} className="text-muted-light" /> Customer since {o.customer.since}
        </span>
      </div>
    </div>
  );
}
