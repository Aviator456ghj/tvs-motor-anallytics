import { Card, CardHeader } from "@/components/ui/Card";
import { recentOrders } from "@/lib/dashboard-data";

export default function RecentOrdersCard() {
  return (
    <Card className="overflow-hidden">
      <CardHeader title="Recent Orders" />
      <div className="overflow-x-auto px-5 pb-4 pt-2">
        <table className="w-full text-[12.5px] border-separate border-spacing-0">
          <thead>
            <tr className="text-left text-muted-light font-medium">
              <th className="pb-2 pr-2 font-medium">Order</th>
              <th className="pb-2 pr-2 font-medium">Customer</th>
              <th className="pb-2 pr-2 font-medium">Total</th>
              <th className="pb-2 pr-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {recentOrders.map((order) => (
              <tr key={order.id} className="border-t border-card-border/70">
                <td className="py-2.5 pr-2 font-medium text-brand-start whitespace-nowrap">{order.id}</td>
                <td className="py-2.5 pr-2 text-foreground whitespace-nowrap">{order.customer}</td>
                <td className="py-2.5 pr-2 text-foreground whitespace-nowrap">{order.total}</td>
                <td className="py-2.5 pr-2">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${
                      order.status === "Paid"
                        ? "bg-success-bg text-success"
                        : "bg-warning-bg text-warning"
                    }`}
                  >
                    {order.status}
                  </span>
                </td>
                <td className="py-2.5 text-muted-light whitespace-nowrap">{order.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
