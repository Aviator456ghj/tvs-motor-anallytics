"use client";

import { Pencil, ShieldCheck, ShieldAlert } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { customers, orderableProducts, shippingMethods, paymentMethods } from "@/lib/create-order-data";
import type { CustomerStepState } from "./StepCustomer";
import type { LineItem } from "./StepProducts";

export default function StepReview({
  customerState,
  lineItems,
  shippingMethodId,
  paymentMethodId,
  fraudRisk,
  onEditStep,
}: {
  customerState: CustomerStepState;
  lineItems: LineItem[];
  shippingMethodId: string;
  paymentMethodId: string;
  fraudRisk: { level: "Low" | "Medium" | "High"; reasons: string[] };
  onEditStep: (step: number) => void;
}) {
  const customer = customers.find((c) => c.id === customerState.customerId);
  const method = shippingMethods.find((m) => m.id === shippingMethodId);
  const payment = paymentMethods.find((m) => m.id === paymentMethodId);

  return (
    <div className="flex flex-col gap-4">
      <ReviewSection title="Customer" onEdit={() => onEditStep(1)}>
        {customer ? (
          <div className="text-[13px] text-foreground">
            {customer.name} · {customer.email} · {customer.phone}
          </div>
        ) : (
          <div className="text-[13px] text-muted-light">No customer selected</div>
        )}
        <div className="text-[12px] text-muted-light mt-1">
          {customerState.salesChannel} · {customerState.warehouse} · Priority: {customerState.priority}
        </div>
        {customerState.tags.length > 0 && <div className="text-[12px] text-muted-light mt-1">Tags: {customerState.tags.join(", ")}</div>}
      </ReviewSection>

      <ReviewSection title={`Products (${lineItems.length})`} onEdit={() => onEditStep(2)}>
        <div className="flex flex-col gap-1.5">
          {lineItems.map((li) => {
            const p = orderableProducts.find((x) => x.id === li.productId);
            if (!p) return null;
            return (
              <div key={li.productId} className="flex items-center justify-between text-[12.5px]">
                <span className="text-foreground">
                  {p.name} × {li.qty}
                </span>
                <span className="text-muted-light">${(p.price * li.qty).toFixed(2)}</span>
              </div>
            );
          })}
          {lineItems.length === 0 && <span className="text-[12.5px] text-muted-light">No items added</span>}
        </div>
      </ReviewSection>

      <ReviewSection title="Shipping" onEdit={() => onEditStep(3)}>
        <div className="text-[13px] text-foreground">{method ? `${method.name} — ${method.carrier}, ${method.eta}` : "Not selected"}</div>
      </ReviewSection>

      <ReviewSection title="Payment" onEdit={() => onEditStep(4)}>
        <div className="text-[13px] text-foreground">{payment ? payment.label : "Not selected"}</div>
      </ReviewSection>

      <Card className="p-5">
        <h3 className="text-[14.5px] font-semibold text-foreground mb-2.5">Fraud Check</h3>
        <div
          className={`rounded-lg p-3 flex items-start gap-2.5 ${
            fraudRisk.level === "Low" ? "bg-success-bg" : fraudRisk.level === "Medium" ? "bg-warning-bg" : "bg-danger-bg"
          }`}
        >
          {fraudRisk.level === "Low" ? (
            <ShieldCheck size={18} className="text-success shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert size={18} className={`shrink-0 mt-0.5 ${fraudRisk.level === "Medium" ? "text-warning" : "text-danger"}`} />
          )}
          <div>
            <div
              className={`text-[12.5px] font-semibold ${
                fraudRisk.level === "Low" ? "text-success" : fraudRisk.level === "Medium" ? "text-warning" : "text-danger"
              }`}
            >
              {fraudRisk.level} Risk
            </div>
            <div className="text-[11.5px] text-muted mt-0.5">
              {fraudRisk.reasons.length > 0 ? fraudRisk.reasons.join(" · ") : "No risk factors detected"}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

function ReviewSection({ title, onEdit, children }: { title: string; onEdit: () => void; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[14.5px] font-semibold text-foreground">{title}</h3>
        <button onClick={onEdit} className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline">
          <Pencil size={12} /> Edit
        </button>
      </div>
      {children}
    </Card>
  );
}
