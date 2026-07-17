import { FileText, CircleCheck, Layers, Clock, PackageSearch, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { orderDetail } from "@/lib/order-detail-data";

export default function OrderKpiStrip() {
  const o = orderDetail;
  const fulfilledCount = o.items.reduce((s, i) => s + i.fulfilled, 0);
  const totalCount = o.items.reduce((s, i) => s + i.qty, 0);

  const cards: { icon: LucideIcon; iconClass: string; label: string; value: string; sub: string; subClass?: string }[] = [
    {
      icon: FileText,
      iconClass: "bg-indigo-50 text-indigo-500",
      label: "Order Total",
      value: `$${o.summary.grandTotal.toFixed(2)}`,
      sub: `${totalCount} items`,
    },
    {
      icon: CircleCheck,
      iconClass: "bg-emerald-50 text-emerald-500",
      label: "Paid Amount",
      value: `$${o.summary.paid.toFixed(2)}`,
      sub: "May 16, 2025",
    },
    {
      icon: Layers,
      iconClass: "bg-amber-50 text-amber-500",
      label: "Fulfilled",
      value: `${fulfilledCount} of ${totalCount} items`,
      sub: "Partially fulfilled",
      subClass: "text-warning",
    },
    {
      icon: Clock,
      iconClass: "bg-violet-50 text-violet-500",
      label: "Expected Delivery",
      value: o.expectedDelivery,
      sub: `via ${o.carrier}`,
    },
    {
      icon: PackageSearch,
      iconClass: "bg-cyan-50 text-cyan-500",
      label: "Tracking Number",
      value: o.trackingNumber,
      sub: o.trackingStatus,
      subClass: "text-info",
    },
  ];

  return (
    <Card className="px-5 py-4">
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-x-6 gap-y-4">
        {cards.map((c) => (
          <div key={c.label} className="flex items-start gap-3">
            <span className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${c.iconClass}`}>
              <c.icon size={16} />
            </span>
            <div className="min-w-0">
              <div className="text-[11.5px] text-muted-light">{c.label}</div>
              <div className="text-[15px] font-bold text-foreground leading-tight truncate">{c.value}</div>
              <div className={`text-[11px] ${c.subClass ?? "text-muted-light"}`}>{c.sub}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
