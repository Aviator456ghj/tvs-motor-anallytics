import { Headphones, Watch, Speaker, ShoppingBag, Smartphone } from "lucide-react";
import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { inventoryAlerts, inventoryAlertMeta } from "@/lib/dashboard-data";

const icons = [Headphones, Watch, Speaker, ShoppingBag, Smartphone];

export default function InventoryAlertsCard() {
  return (
    <Card>
      <CardHeader title="Inventory Alerts" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5">
        {inventoryAlerts.map((item, i) => {
          const Icon = icons[i % icons.length];
          const meta = inventoryAlertMeta[item.type];
          return (
            <div key={item.id} className="flex items-center gap-3">
              <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                <Icon size={16} />
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] text-foreground truncate">{item.name}</div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0 ${meta.bgClass} ${meta.textClass}`}>
                    {meta.label}
                  </span>
                  <span className="text-[11px] text-muted-light truncate">{item.status}</span>
                </div>
              </div>
              <span className={`text-[13px] font-semibold shrink-0 ${item.type === "out" ? "text-danger" : "text-foreground"}`}>
                {item.count}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
