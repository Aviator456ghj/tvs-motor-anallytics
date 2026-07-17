import { Mail, MessageCircle, Wallet, ArrowUp, type LucideIcon } from "lucide-react";
import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { marketingPerformance } from "@/lib/dashboard-data";

const iconMap: Record<string, LucideIcon> = {
  mail: Mail,
  sms: MessageCircle,
  spend: Wallet,
};

const brandBadge: Record<string, { label: string; className: string }> = {
  facebook: { label: "f", className: "bg-[#1877F2] text-white" },
  google: { label: "G", className: "bg-white text-[#EA4335] border border-card-border" },
};

export default function MarketingPerformanceCard() {
  return (
    <Card>
      <CardHeader title="Marketing Performance" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5">
        {marketingPerformance.map((item) => {
          const Icon = iconMap[item.icon];
          const badge = brandBadge[item.icon];
          return (
            <div key={item.id} className="flex items-center gap-3">
              <span className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 text-[13px] font-bold ${item.bg} ${item.color}`}>
                {Icon ? <Icon size={15} /> : badge ? <span className={`w-full h-full rounded-lg flex items-center justify-center ${badge.className}`}>{badge.label}</span> : null}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] text-foreground truncate">{item.name}</div>
                <div className="text-[11.5px] text-muted-light">{item.metric}</div>
              </div>
              <span className="text-[13px] font-semibold text-foreground shrink-0">{item.value}</span>
              <span className="flex items-center gap-0.5 text-[11.5px] font-medium text-success shrink-0">
                <ArrowUp size={11} />
                {item.delta}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
