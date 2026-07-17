import { Package } from "lucide-react";
import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { topReturnedProducts } from "@/lib/returns-data";

export default function TopReturnedProducts() {
  return (
    <Card>
      <CardHeader title="Top Returned Products" action={<ViewAllLink />} />
      <div className="px-5 pb-5 pt-2 flex flex-col gap-3">
        {topReturnedProducts.map((p, i) => (
          <div key={p.id} className="flex items-center gap-3">
            <span className="w-4 text-[12.5px] text-muted-light shrink-0">{i + 1}</span>
            <span className="w-8 h-8 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
              <Package size={14} />
            </span>
            <span className="flex-1 text-[13px] text-foreground truncate">{p.name}</span>
            <span className="text-[12px] text-muted-light shrink-0">{p.returns} returns</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
