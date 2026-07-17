import { PlusSquare, Upload, Download, RotateCcw, ListChecks, FileText, Receipt, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { quickActions, paymentStatusLegend, fulfillmentStatusLegend, orderStatusLegend } from "@/lib/orders-data";

const iconMap: Record<string, LucideIcon> = {
  "plus-square": PlusSquare,
  upload: Upload,
  download: Download,
  "rotate-ccw": RotateCcw,
  "list-checks": ListChecks,
  "file-text": FileText,
  receipt: Receipt,
};

export default function OrdersRightSidebar() {
  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Quick Actions</h3>
        <div className="flex flex-col gap-1">
          {quickActions.map((action) => {
            const Icon = iconMap[action.icon];
            const content = (
              <>
                <span className="w-7 h-7 rounded-lg bg-background flex items-center justify-center text-brand-start shrink-0">
                  <Icon size={14} />
                </span>
                {action.label}
              </>
            );
            const className = "flex items-center gap-2.5 rounded-lg px-2 py-2 text-[12.5px] font-medium text-foreground hover:bg-background/80 text-left";
            return action.label === "Create Order" ? (
              <a key={action.id} href="/orders/create" className={className}>
                {content}
              </a>
            ) : (
              <button key={action.id} className={className}>
                {content}
              </button>
            );
          })}
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[13.5px] font-semibold text-foreground">Order Statuses</h3>
        </div>

        <LegendGroup title="Payment Status" items={paymentStatusLegend} />
        <LegendGroup title="Fulfillment Status" items={fulfillmentStatusLegend} className="mt-4" />
        <LegendGroup title="Order Status" items={orderStatusLegend} className="mt-4" />
      </Card>
    </div>
  );
}

function LegendGroup({
  title,
  items,
  className = "",
}: {
  title: string;
  items: { label: string; description: string; color: string; bg: string }[];
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-light mb-2">{title}</div>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10.5px] font-medium w-[104px] text-center ${item.bg} ${item.color}`}>
              {item.label}
            </span>
            <span className="text-[11.5px] text-muted-light">{item.description}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
