"use client";

import { CreditCard, Banknote, Landmark, Clock, Split } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { paymentMethods } from "@/lib/create-order-data";

const iconMap: Record<string, typeof CreditCard> = {
  card: CreditCard,
  cash: Banknote,
  "bank-transfer": Landmark,
  "pay-later": Clock,
  split: Split,
};

export default function StepPayment({
  selectedId,
  onSelect,
  grandTotal,
}: {
  selectedId: string;
  onSelect: (id: string) => void;
  grandTotal: number;
}) {
  return (
    <div className="flex flex-col gap-4">
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[14.5px] font-semibold text-foreground">Payment Method</h3>
          <span className="text-[13px] text-muted">
            Amount due: <span className="font-semibold text-foreground">${grandTotal.toFixed(2)}</span>
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {paymentMethods.map((m) => {
            const Icon = iconMap[m.id];
            return (
              <label
                key={m.id}
                className={`flex items-center gap-3 rounded-lg border p-3.5 cursor-pointer transition-colors ${
                  selectedId === m.id ? "border-brand-start bg-brand-start/[0.04]" : "border-card-border hover:bg-background/60"
                }`}
              >
                <input type="radio" checked={selectedId === m.id} onChange={() => onSelect(m.id)} className="accent-brand-start" />
                <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                  <Icon size={16} />
                </span>
                <span>
                  <div className="text-[13px] font-medium text-foreground">{m.label}</div>
                  <div className="text-[11.5px] text-muted-light">{m.description}</div>
                </span>
              </label>
            );
          })}
        </div>
      </Card>

      {selectedId === "card" && (
        <Card className="p-5">
          <h3 className="text-[14.5px] font-semibold text-foreground mb-3">Card Details</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input placeholder="Card number" className="rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2 sm:col-span-2" />
            <input placeholder="MM / YY" className="rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2" />
            <input placeholder="CVC" className="rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2" />
          </div>
        </Card>
      )}

      {selectedId === "split" && (
        <Card className="p-5">
          <h3 className="text-[14.5px] font-semibold text-foreground mb-3">Split Payment</h3>
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-2.5">
              <select className="flex-1 rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2">
                <option>Credit / Debit Card</option>
                <option>Cash</option>
                <option>Bank Transfer</option>
              </select>
              <input
                defaultValue={(grandTotal / 2).toFixed(2)}
                className="w-28 rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2"
              />
            </div>
            <div className="flex items-center gap-2.5">
              <select className="flex-1 rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2">
                <option>Cash</option>
                <option>Credit / Debit Card</option>
                <option>Bank Transfer</option>
              </select>
              <input
                defaultValue={(grandTotal / 2).toFixed(2)}
                className="w-28 rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2"
              />
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
