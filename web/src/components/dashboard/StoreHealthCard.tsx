import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { storeHealth } from "@/lib/dashboard-data";

export default function StoreHealthCard() {
  return (
    <Card>
      <CardHeader title="Store Health" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5">
        {storeHealth.map((item) => (
          <div key={item.id} className="flex items-center gap-3">
            <span className="flex-1 text-[13px] text-muted truncate">{item.label}</span>
            <span className="text-[13px] text-foreground text-right shrink-0">{item.value}</span>
            <span
              className={`flex items-center gap-1.5 text-[11.5px] font-medium shrink-0 w-[62px] justify-end ${
                item.level === "good" ? "text-success" : "text-warning"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${item.level === "good" ? "bg-success" : "bg-warning"}`} />
              {item.status}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
