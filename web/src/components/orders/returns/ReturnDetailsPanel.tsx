import { Package } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { statusStyle, selectedReturnDetail, type ReturnRequest } from "@/lib/returns-data";

export default function ReturnDetailsPanel({ selected }: { selected: ReturnRequest }) {
  const d = selectedReturnDetail;

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-[14.5px] font-semibold text-foreground">{selected.id}</h3>
        <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${statusStyle[selected.status]}`}>{selected.status}</span>
      </div>
      <div className="flex flex-col gap-1.5 mb-3">
        <Row label="Order ID" value={selected.orderId} link />
        <Row label="Customer" value={selected.customer} />
        <Row label="Requested On" value={selected.requestedOn} />
        <Row label="Return Type" value={d.returnType} />
        <Row label="Reason" value={selected.reason} />
      </div>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-1.5">Notes</div>
      <p className="text-[12px] text-muted mb-3">{d.notes}</p>

      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-2">Items ({d.items.length})</div>
      <div className="flex flex-col gap-2.5 mb-3">
        {d.items.map((item) => (
          <div key={item.sku} className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
              <Package size={15} />
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-medium text-foreground truncate">{item.name}</div>
              <div className="text-[11px] text-muted-light">
                {item.variant} · {item.sku}
              </div>
            </div>
            <span className="text-[11.5px] text-muted-light shrink-0">Qty: {item.qty}</span>
          </div>
        ))}
      </div>

      <div className="border-t border-card-border pt-2.5 flex items-center justify-between">
        <span className="text-[13px] font-semibold text-foreground">Total Refund Amount</span>
        <span className="text-[15px] font-bold text-foreground">${d.totalRefund.toFixed(2)}</span>
      </div>
    </Card>
  );
}

function Row({ label, value, link }: { label: string; value: string; link?: boolean }) {
  return (
    <div className="flex items-center justify-between text-[12.5px]">
      <span className="text-muted">{label}</span>
      <span className={link ? "text-brand-start font-medium" : "text-foreground font-medium"}>{value}</span>
    </div>
  );
}
