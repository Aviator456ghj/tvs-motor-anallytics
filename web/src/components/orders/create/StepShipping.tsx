"use client";

import { Truck } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { shippingMethods } from "@/lib/create-order-data";

export default function StepShipping({
  selectedId,
  onSelect,
  instructions,
  onInstructionsChange,
}: {
  selectedId: string;
  onSelect: (id: string) => void;
  instructions: string;
  onInstructionsChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <Card className="p-5">
        <h3 className="text-[14.5px] font-semibold text-foreground mb-3">Shipping Method</h3>
        <div className="flex flex-col gap-2.5">
          {shippingMethods.map((m) => (
            <label
              key={m.id}
              className={`flex items-center gap-3 rounded-lg border p-3.5 cursor-pointer transition-colors ${
                selectedId === m.id ? "border-brand-start bg-brand-start/[0.04]" : "border-card-border hover:bg-background/60"
              }`}
            >
              <input type="radio" checked={selectedId === m.id} onChange={() => onSelect(m.id)} className="accent-brand-start" />
              <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                <Truck size={16} />
              </span>
              <span className="flex-1">
                <div className="text-[13px] font-medium text-foreground">{m.name}</div>
                <div className="text-[11.5px] text-muted-light">
                  {m.carrier} · {m.eta}
                </div>
              </span>
              <span className="text-[13.5px] font-semibold text-foreground">{m.price === 0 ? "Free" : `$${m.price.toFixed(2)}`}</span>
            </label>
          ))}
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-[14.5px] font-semibold text-foreground mb-2">Delivery Instructions</h3>
        <textarea
          value={instructions}
          onChange={(e) => onInstructionsChange(e.target.value)}
          rows={3}
          placeholder="e.g. Leave at front desk, call on arrival..."
          className="w-full rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2 placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30"
        />
      </Card>
    </div>
  );
}
