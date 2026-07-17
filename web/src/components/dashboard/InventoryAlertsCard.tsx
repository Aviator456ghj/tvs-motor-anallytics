import { Headphones, Watch, Speaker, Briefcase, Smartphone } from "lucide-react";
import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { inventoryAlerts } from "@/lib/dashboard-data";

const icons = [Headphones, Watch, Speaker, Briefcase, Smartphone];

export default function InventoryAlertsCard() {
  return (
    <Card>
      <CardHeader title="Inventory Alerts" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5">
        {inventoryAlerts.map((item, i) => {
          const Icon = icons[i % icons.length];
          return (
            <div key={item.id} className="flex items-center gap-3">
              <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                <Icon size={16} />
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] text-foreground truncate">{item.name}</div>
                <div
                  className={`text-[11.5px] font-medium ${
                    item.level === "out" ? "text-danger" : item.level === "low" ? "text-warning" : "text-muted"
                  }`}
                >
                  {item.status}
                </div>
              </div>
              <span
                className={`text-[13px] font-semibold shrink-0 ${
                  item.level === "out" ? "text-danger" : "text-foreground"
                }`}
              >
                {item.count}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
