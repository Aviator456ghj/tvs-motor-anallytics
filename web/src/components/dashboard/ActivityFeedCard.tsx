import { ShoppingBag, CreditCard, UserPlus, Package, Percent, Boxes, Settings, type LucideIcon } from "lucide-react";
import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { activityFeed, type ActivityType } from "@/lib/dashboard-data";

const iconMap: Record<ActivityType, LucideIcon> = {
  order: ShoppingBag,
  payment: CreditCard,
  customer: UserPlus,
  product: Package,
  discount: Percent,
  inventory: Boxes,
  system: Settings,
};

const colorMap: Record<ActivityType, string> = {
  order: "bg-blue-50 text-blue-500",
  payment: "bg-emerald-50 text-emerald-500",
  customer: "bg-indigo-50 text-indigo-500",
  product: "bg-amber-50 text-amber-500",
  discount: "bg-orange-50 text-orange-500",
  inventory: "bg-rose-50 text-rose-500",
  system: "bg-slate-100 text-slate-500",
};

export default function ActivityFeedCard() {
  return (
    <Card>
      <CardHeader title="Activity Feed" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5 max-h-[220px] overflow-y-auto">
        {activityFeed.map((item) => {
          const Icon = iconMap[item.type];
          return (
            <div key={item.id} className="flex items-start gap-3">
              <span className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${colorMap[item.type]}`}>
                <Icon size={13} />
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] text-foreground leading-snug">{item.text}</div>
                <div className="text-[11px] text-muted-light">{item.actor} · {item.time}</div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
