import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { recentActivity, exceptionOrders } from "@/lib/fulfillment-data";

export default function ActivityAndExceptions() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Card>
        <CardHeader title="Recent Activity" action={<ViewAllLink />} />
        <div className="px-5 pb-4 pt-2 flex flex-col gap-3">
          {recentActivity.map((a) => (
            <div key={a.id} className="flex items-start gap-3 text-[12.5px]">
              <span className="text-muted-light w-16 shrink-0">{a.time}</span>
              <span className="flex-1 text-foreground">{a.text}</span>
              <span className="text-muted-light shrink-0">by {a.actor}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title="Exception Orders" action={<ViewAllLink />} />
        <div className="px-5 pb-4 pt-2 flex flex-col gap-3">
          {exceptionOrders.map((e) => (
            <div key={e.id} className="flex items-center gap-3 text-[12.5px]">
              <span className="text-danger font-medium w-20 shrink-0">{e.id}</span>
              <span className="flex-1 text-foreground truncate">{e.reason}</span>
              <span className="text-muted-light shrink-0">{e.date}</span>
              <span
                className={`shrink-0 px-1.5 py-0.5 rounded text-[10.5px] font-medium ${
                  e.severity === "High" ? "bg-danger-bg text-danger" : e.severity === "Medium" ? "bg-warning-bg text-warning" : "bg-success-bg text-success"
                }`}
              >
                {e.severity}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
