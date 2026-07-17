"use client";

import { useState } from "react";
import { Printer, RotateCcw, ChevronLeft, ChevronRight, Mail, Phone, MapPin, CheckCircle2, Circle, ExternalLink } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { orderTimeline, orderDetailItems, type Order, type PaymentStatus, type FulfillmentStatus } from "@/lib/orders-data";

const paymentBadge: Record<PaymentStatus, string> = {
  Paid: "bg-success-bg text-success",
  Pending: "bg-warning-bg text-warning",
  "Partially Paid": "bg-orange-50 text-orange-600",
  Refunded: "bg-info-bg text-info",
  Voided: "bg-card-border/60 text-muted",
};

const fulfillmentBadge: Record<FulfillmentStatus, string> = {
  Unfulfilled: "bg-warning-bg text-warning",
  "Partially Fulfilled": "bg-orange-50 text-orange-600",
  Fulfilled: "bg-success-bg text-success",
  Backordered: "bg-danger-bg text-danger",
};

export default function OrderDetailPanel({ order }: { order: Order }) {
  const [note, setNote] = useState("");
  const completedSteps = order.fulfillment === "Fulfilled" ? 5 : order.fulfillment === "Partially Fulfilled" ? 3 : 2;

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-card-border">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-[15px] font-semibold text-foreground">Order {order.id}</h3>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${paymentBadge[order.payment]}`}>{order.payment}</span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${fulfillmentBadge[order.fulfillment]}`}>{order.fulfillment}</span>
          </div>
          <div className="flex items-center gap-2 text-[12px] text-muted-light mt-1">
            <span>{order.date}</span>
            <span>·</span>
            <span>{order.channel}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">
            <Printer size={13} /> Print
          </button>
          <button className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">
            <RotateCcw size={13} /> Refund
          </button>
          <button className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">
            More actions <ExternalLink size={12} />
          </button>
          <div className="flex items-center gap-1 ml-1">
            <button className="w-7 h-7 flex items-center justify-center rounded-lg border border-card-border text-muted hover:bg-background/80">
              <ChevronLeft size={14} />
            </button>
            <button className="w-7 h-7 flex items-center justify-center rounded-lg border border-card-border text-muted hover:bg-background/80">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      <div className="p-5 grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="flex flex-col gap-1.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light">Customer</div>
          <div className="text-[13.5px] font-medium text-foreground">{order.customer}</div>
          <div className="flex items-center gap-1.5 text-[12px] text-muted"><Mail size={12} />{order.email}</div>
          <div className="flex items-center gap-1.5 text-[12px] text-muted"><Phone size={12} />{order.phone}</div>
          <a href="#" className="text-[12px] font-medium text-brand-start hover:underline mt-1">View customer</a>
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light">Order summary</div>
          <Row label="Subtotal" value={`$${order.subtotal.toFixed(2)}`} />
          <Row label="Shipping" value={`$${order.shipping.toFixed(2)}`} />
          <Row label="Tax" value={`$${order.tax.toFixed(2)}`} />
          <div className="border-t border-card-border pt-1.5 mt-0.5">
            <Row label="Total" value={`$${order.total.toFixed(2)}`} bold />
          </div>
          <div className="text-[11.5px] text-muted-light mt-1">Paid by Visa •••• 4242</div>
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light">Shipping address</div>
          <div className="text-[12.5px] text-foreground leading-snug">
            {order.customer}<br />
            123 Main Street<br />
            New York, NY 10001<br />
            United States
          </div>
          <a href="#" className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline mt-1">
            <MapPin size={12} /> View map
          </a>
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light">Order timeline</div>
          {orderTimeline.map((step, i) => {
            const done = i < completedSteps;
            return (
              <div key={step.label} className="flex items-center gap-2 text-[12px]">
                {done ? <CheckCircle2 size={13} className="text-success shrink-0" /> : <Circle size={13} className="text-card-border shrink-0" />}
                <span className={done ? "text-foreground" : "text-muted-light"}>{step.label}</span>
                {done && <span className="text-muted-light ml-auto whitespace-nowrap">{step.time}</span>}
              </div>
            );
          })}
        </div>
      </div>

      <div className="px-5 pb-5">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-2">Items ({orderDetailItems.length})</div>
        <div className="overflow-x-auto border border-card-border rounded-lg">
          <table className="w-full text-[12.5px] border-separate border-spacing-0">
            <thead>
              <tr className="text-left text-muted-light font-medium bg-background/60">
                <th className="py-2 pl-3 pr-2 font-medium">Item</th>
                <th className="py-2 pr-2 font-medium">SKU</th>
                <th className="py-2 pr-2 font-medium">Price</th>
                <th className="py-2 pr-2 font-medium">Qty</th>
                <th className="py-2 pr-3 font-medium text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {orderDetailItems.map((item) => (
                <tr key={item.sku} className="border-t border-card-border/70">
                  <td className="py-2.5 pl-3 pr-2">
                    <div className="flex items-center gap-2.5">
                      <span className="w-9 h-9 rounded-lg bg-background shrink-0" />
                      <div>
                        <div className="text-foreground font-medium">{item.name}</div>
                        <div className="text-muted-light text-[11.5px]">{item.variant}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-2.5 pr-2 text-muted whitespace-nowrap">{item.sku}</td>
                  <td className="py-2.5 pr-2 text-muted whitespace-nowrap">${item.price.toFixed(2)}</td>
                  <td className="py-2.5 pr-2 text-muted whitespace-nowrap">{item.qty}</td>
                  <td className="py-2.5 pr-3 text-foreground font-medium text-right whitespace-nowrap">${item.total.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Add item</button>
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Edit items</button>
        </div>
      </div>

      <div className="px-5 pb-5">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light">Notes</div>
          <button className="text-[12px] font-medium text-brand-start hover:underline">Add note</button>
        </div>
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="No notes added"
          className="w-full rounded-lg border border-card-border bg-background/60 text-[12.5px] px-3 py-2 placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30"
        />
      </div>
    </Card>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between text-[12.5px]">
      <span className="text-muted">{label}</span>
      <span className={bold ? "font-semibold text-foreground" : "text-foreground"}>{value}</span>
    </div>
  );
}
