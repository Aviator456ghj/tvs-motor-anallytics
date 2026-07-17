import { UserPlus, Repeat, RotateCcw, HeartHandshake, TrendingDown, ArrowUp, type LucideIcon } from "lucide-react";
import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { customerInsights } from "@/lib/dashboard-data";

const icons: LucideIcon[] = [UserPlus, Repeat, RotateCcw, HeartHandshake, TrendingDown];

export default function CustomerInsightsCard() {
  return (
    <Card>
      <CardHeader title="Customer Insights" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5">
        {customerInsights.map((item, i) => {
          const Icon = icons[i % icons.length];
          return (
            <div key={item.id} className="flex items-center gap-3">
              <span className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${item.bg} ${item.color}`}>
                <Icon size={15} />
              </span>
              <span className="flex-1 text-[13px] text-foreground truncate">{item.label}</span>
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
