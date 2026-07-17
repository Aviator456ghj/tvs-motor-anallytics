import { Headphones, Watch, Speaker, Briefcase, Smartphone } from "lucide-react";
import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { topProducts } from "@/lib/dashboard-data";

const icons = [Headphones, Watch, Speaker, Briefcase, Smartphone];

export default function TopProductsCard() {
  return (
    <Card>
      <CardHeader title="Top Products" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5">
        {topProducts.map((item, i) => {
          const Icon = icons[i % icons.length];
          return (
            <div key={item.id} className="flex items-center gap-3">
              <span className="w-3.5 text-[12.5px] text-muted-light shrink-0">{i + 1}</span>
              <span className="w-8 h-8 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                <Icon size={14} />
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] text-foreground truncate">{item.name}</div>
                <div className="text-[11.5px] text-muted-light">{item.sold} sold</div>
              </div>
              <span className="text-[13px] font-semibold text-foreground shrink-0 text-right">{item.revenue}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
