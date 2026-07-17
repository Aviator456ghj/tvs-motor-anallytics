"use client";

import { CheckCircle2, Circle, Copy, MapPin, ExternalLink, Plus, Crown } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { orderDetail, paymentStatusStyle } from "@/lib/order-detail-data";
import ItemsTable from "./ItemsTable";

export default function OverviewTab() {
  const o = orderDetail;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
      {/* Column 1 */}
      <div className="flex flex-col gap-4 min-w-0">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[14px] font-semibold text-foreground">Customer Information</h3>
            <button className="text-[12px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1 hover:bg-background/80">Edit</button>
          </div>
          <div className="flex items-center gap-3 mb-3">
            <span className="w-11 h-11 rounded-full bg-gradient-to-br from-brand-start to-brand-end flex items-center justify-center text-white text-[13px] font-semibold shrink-0">
              JS
            </span>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-[13.5px] font-semibold text-foreground">{o.customer.name}</span>
                {o.customer.vip && (
                  <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-success-bg text-success text-[10px] font-semibold">
                    <Crown size={9} /> VIP
                  </span>
                )}
              </div>
              <div className="text-[12px] text-muted-light">{o.customer.email}</div>
              <div className="text-[12px] text-muted-light">{o.customer.phone}</div>
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <InfoRow label="Total Orders" value={String(o.customer.totalOrders)} />
            <InfoRow label="Total Spent" value={`$${o.customer.totalSpent.toFixed(2)}`} />
            <InfoRow label="Outstanding" value={`$${o.customer.outstanding.toFixed(2)}`} valueClass="text-danger font-semibold" />
          </div>
          <a href="#" className="flex items-center gap-1 text-[12.5px] font-medium text-brand-start hover:underline mt-3">
            View full customer profile <ExternalLink size={12} />
          </a>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[14px] font-semibold text-foreground">Billing Address</h3>
            <button className="text-[12px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1 hover:bg-background/80">Edit</button>
          </div>
          <div className="text-[12.5px] text-foreground leading-relaxed">
            {o.billingAddress.name}
            <br />
            {o.billingAddress.line1}
            <br />
            {o.billingAddress.city}, {o.billingAddress.state} {o.billingAddress.postalCode}
            <br />
            {o.billingAddress.country}
            <br />
            {o.billingAddress.phone}
          </div>
          <a href="#" className="flex items-center gap-1 text-[12.5px] font-medium text-brand-start hover:underline mt-3">
            View map <MapPin size={12} />
          </a>
        </Card>
      </div>

      {/* Column 2 */}
      <div className="flex flex-col gap-4 min-w-0">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[14px] font-semibold text-foreground">Shipping Address</h3>
            <button className="text-[12px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1 hover:bg-background/80">Edit</button>
          </div>
          <div className="text-[12.5px] text-foreground leading-relaxed">
            {o.shippingAddress.name}
            <br />
            {o.shippingAddress.line1}
            <br />
            {o.shippingAddress.city}, {o.shippingAddress.state} {o.shippingAddress.postalCode}
            <br />
            {o.shippingAddress.country}
            <br />
            {o.shippingAddress.phone}
          </div>
          <div className="flex flex-col gap-1.5 mt-3 pt-3 border-t border-card-border">
            <InfoRow label="Method" value={o.shippingMethod} />
            <div className="flex items-center justify-between text-[12.5px]">
              <span className="text-muted">Tracking</span>
              <span className="flex items-center gap-1.5">
                <span className="text-foreground font-medium">{o.trackingNumber}</span>
                <button className="text-muted-light hover:text-muted" title="Copy">
                  <Copy size={12} />
                </button>
                <span className="px-1.5 py-0.5 rounded-full bg-info-bg text-info text-[10.5px] font-medium">{o.trackingStatus}</span>
              </span>
            </div>
            <InfoRow label="Warehouse" value={o.warehouse} />
            <InfoRow label="Package Weight" value={o.packageWeight} />
          </div>
          <a href="#" className="flex items-center gap-1 text-[12.5px] font-medium text-brand-start hover:underline mt-3">
            View on FedEx <ExternalLink size={12} />
          </a>
        </Card>

        <Card className="p-5">
          <h3 className="text-[14px] font-semibold text-foreground mb-3">Order Summary</h3>
          <div className="flex flex-col gap-1.5">
            <InfoRow label="Items Total" value={`$${o.summary.itemsTotal.toFixed(2)}`} />
            <InfoRow label={`Discount (${o.summary.coupon})`} value={`-$${o.summary.discount.toFixed(2)}`} valueClass="text-success" />
            <InfoRow label="Shipping" value={`$${o.summary.shipping.toFixed(2)}`} />
            <InfoRow label={o.summary.taxLabel} value={`$${o.summary.tax.toFixed(2)}`} />
          </div>
          <div className="border-t border-card-border mt-2.5 pt-2.5 flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[13.5px] font-semibold text-foreground">Grand Total</span>
              <span className="text-[16px] font-bold text-foreground">${o.summary.grandTotal.toFixed(2)}</span>
            </div>
            <InfoRow label="Paid" value={`$${o.summary.paid.toFixed(2)}`} valueClass="text-success font-medium" />
            <InfoRow label="Due" value={`$${o.summary.due.toFixed(2)}`} />
          </div>
        </Card>
      </div>

      {/* Column 3 */}
      <div className="flex flex-col gap-4 min-w-0">
        <Card className="p-5">
          <h3 className="text-[14px] font-semibold text-foreground mb-3">Order Status</h3>
          <div className="flex flex-col gap-2.5">
            {o.statusSteps.map((step) => (
              <div key={step.label} className="flex items-center gap-2.5 text-[12.5px]">
                {step.done ? (
                  <CheckCircle2 size={15} className="text-success shrink-0" />
                ) : (
                  <Circle size={15} className="text-card-border shrink-0" />
                )}
                <span className={step.done ? "text-foreground font-medium" : "text-muted-light"}>{step.label}</span>
                {step.time && <span className="ml-auto text-[11.5px] text-muted-light whitespace-nowrap">{step.time}</span>}
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[14px] font-semibold text-foreground">Payment Information</h3>
            <button className="text-[12px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1 hover:bg-background/80">Edit</button>
          </div>
          <div className="flex flex-col gap-1.5">
            <InfoRow label="Method" value={o.payment.method} />
            <InfoRow label="Transaction ID" value={o.payment.transactionId} />
            <InfoRow label="Captured On" value={o.payment.capturedOn} />
            <div className="flex items-center justify-between text-[12.5px]">
              <span className="text-muted">Status</span>
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${paymentStatusStyle[o.payment.status]}`}>{o.payment.status}</span>
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[14px] font-semibold text-foreground">Tags</h3>
            <button className="text-[12px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1 hover:bg-background/80">Edit</button>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {o.tags.map((t, i) => (
              <span
                key={t}
                className={`px-2 py-1 rounded-full text-[11px] font-medium ${
                  i === 0 ? "bg-success-bg text-success" : i === 1 ? "bg-info-bg text-info" : "bg-warning-bg text-warning"
                }`}
              >
                {t}
              </span>
            ))}
            <button className="flex items-center gap-0.5 px-2 py-1 rounded-full border border-dashed border-card-border text-[11px] text-muted hover:bg-background/80">
              <Plus size={10} /> Add Tag
            </button>
          </div>
        </Card>
      </div>

      {/* Full-width items table */}
      <div className="xl:col-span-3 min-w-0">
        <ItemsTable />
      </div>
    </div>
  );
}

function InfoRow({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex items-center justify-between text-[12.5px]">
      <span className="text-muted">{label}</span>
      <span className={valueClass ?? "text-foreground font-medium"}>{value}</span>
    </div>
  );
}
