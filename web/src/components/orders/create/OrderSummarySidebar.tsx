"use client";

import { useState } from "react";
import { Tag, Plus, Percent, Gift, StickyNote, Sparkles, Check, X } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { quickActions, type Coupon } from "@/lib/create-order-data";

const quickActionIcons: Record<string, typeof Plus> = {
  plus: Plus,
  percent: Percent,
  gift: Gift,
  note: StickyNote,
};

export default function OrderSummarySidebar({
  itemsTotal,
  discount,
  shipping,
  taxRate,
  tax,
  grandTotal,
  savings,
  appliedCoupon,
  onApplyCoupon,
  onRemoveCoupon,
  couponError,
  onQuickAction,
}: {
  itemsTotal: number;
  discount: number;
  shipping: number;
  taxRate: number;
  tax: number;
  grandTotal: number;
  savings: number;
  appliedCoupon: Coupon | null;
  onApplyCoupon: (code: string) => void;
  onRemoveCoupon: () => void;
  couponError: string | null;
  onQuickAction: (id: number) => void;
}) {
  const [couponInput, setCouponInput] = useState("");

  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Order Summary</h3>
        <div className="flex flex-col gap-2">
          <Row label="Items Total" value={`$${itemsTotal.toFixed(2)}`} />
          <Row label="Discount" value={`-$${discount.toFixed(2)}`} valueClass={discount > 0 ? "text-success" : undefined} />
          <Row label="Shipping" value={`$${shipping.toFixed(2)}`} />
          <Row label={`Tax (${(taxRate * 100).toFixed(2)}%)`} value={`$${tax.toFixed(2)}`} />
        </div>
        <div className="border-t border-card-border mt-3 pt-3 flex items-center justify-between">
          <span className="text-[14px] font-semibold text-foreground">Grand Total</span>
          <span className="text-[19px] font-bold text-brand-start">${grandTotal.toFixed(2)}</span>
        </div>
        {savings > 0 && (
          <div className="flex items-center justify-between mt-2 text-[12px]">
            <span className="flex items-center gap-1 text-success">
              <Tag size={12} /> Total Savings
            </span>
            <span className="text-success font-medium">${savings.toFixed(2)}</span>
          </div>
        )}
      </Card>

      <Card className="p-4">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-2.5">Apply Coupon</h3>
        {appliedCoupon ? (
          <div className="flex items-center justify-between rounded-lg bg-success-bg px-3 py-2">
            <span className="flex items-center gap-1.5 text-[12.5px] font-medium text-success">
              <Check size={13} /> {appliedCoupon.code}
            </span>
            <button onClick={onRemoveCoupon} className="text-success hover:text-danger">
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              value={couponInput}
              onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
              placeholder="Enter coupon code"
              className="flex-1 min-w-0 rounded-lg border border-card-border bg-background/60 text-[12.5px] px-3 py-2 placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30"
            />
            <button
              onClick={() => onApplyCoupon(couponInput)}
              className="text-[12.5px] font-medium text-white bg-brand-start rounded-lg px-3.5 py-2 hover:opacity-90 shrink-0"
            >
              Apply
            </button>
          </div>
        )}
        {couponError && <div className="text-[11.5px] text-danger mt-1.5">{couponError}</div>}
      </Card>

      <Card className="p-4">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-2">Quick Actions</h3>
        <div className="flex flex-col gap-1">
          {quickActions.map((qa) => {
            const Icon = quickActionIcons[qa.icon];
            return (
              <button
                key={qa.id}
                onClick={() => onQuickAction(qa.id)}
                className="flex items-center gap-2.5 rounded-lg px-2 py-2 text-[12.5px] font-medium text-foreground hover:bg-background/80 text-left"
              >
                <span className="w-7 h-7 rounded-lg bg-background flex items-center justify-center text-brand-start shrink-0">
                  <Icon size={14} />
                </span>
                {qa.label}
              </button>
            );
          })}
        </div>
      </Card>

      <Card className="p-4 bg-gradient-to-br from-brand-start to-brand-end text-white border-none">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[13px] font-semibold flex items-center gap-1.5">
            <Sparkles size={14} /> AI Assistant
          </h3>
          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-white/20">Beta</span>
        </div>
        <p className="text-[12px] text-white/85 leading-snug">
          Need help creating this order? Ask me to suggest products, check customer history, apply best discounts and more.
        </p>
        <button className="w-full mt-3 flex items-center justify-center gap-1.5 rounded-lg bg-white text-brand-start text-[12.5px] font-semibold py-2 hover:opacity-90">
          <Sparkles size={13} />
          Ask AI Assistant
        </button>
      </Card>
    </div>
  );
}

function Row({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex items-center justify-between text-[12.5px]">
      <span className="text-muted">{label}</span>
      <span className={valueClass ?? "text-foreground font-medium"}>{value}</span>
    </div>
  );
}
