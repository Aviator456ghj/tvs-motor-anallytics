"use client";

import { useState } from "react";
import { MoreHorizontal, Eye, Pencil, RotateCcw, Printer, Archive } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { recentOrders, orderActions, type OrderActionKey } from "@/lib/dashboard-data";

const actionIcons: Record<OrderActionKey, typeof Eye> = {
  view: Eye,
  edit: Pencil,
  refund: RotateCcw,
  print: Printer,
  archive: Archive,
};

function paymentBadgeClass(status: string) {
  if (status === "Paid") return "bg-success-bg text-success";
  if (status === "Pending") return "bg-warning-bg text-warning";
  return "bg-info-bg text-info";
}

function fulfillmentBadgeClass(status: string) {
  if (status === "Fulfilled") return "bg-success-bg text-success";
  if (status === "Partial") return "bg-warning-bg text-warning";
  return "bg-card-border/60 text-muted";
}

export default function RecentOrdersCard() {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

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
              <th className="pb-2 pr-2 font-medium">Payment</th>
              <th className="pb-2 pr-2 font-medium">Fulfillment</th>
              <th className="pb-2 pr-2 font-medium">Date</th>
              <th className="pb-2 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {recentOrders.map((order) => (
              <tr key={order.id} className="border-t border-card-border/70">
                <td className="py-2.5 pr-2 font-medium text-brand-start whitespace-nowrap">{order.id}</td>
                <td className="py-2.5 pr-2 text-foreground whitespace-nowrap">{order.customer}</td>
                <td className="py-2.5 pr-2 text-foreground whitespace-nowrap">{order.total}</td>
                <td className="py-2.5 pr-2">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${paymentBadgeClass(order.payment)}`}>
                    {order.payment}
                  </span>
                </td>
                <td className="py-2.5 pr-2">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${fulfillmentBadgeClass(order.fulfillment)}`}>
                    {order.fulfillment}
                  </span>
                </td>
                <td className="py-2.5 pr-2 text-muted-light whitespace-nowrap">{order.date}</td>
                <td className="py-2.5 text-right relative">
                  <button
                    onClick={() => setOpenMenuId((v) => (v === order.id ? null : order.id))}
                    className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80"
                  >
                    <MoreHorizontal size={15} />
                  </button>
                  {openMenuId === order.id && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
                      <div className="absolute right-0 top-full mt-1 w-32 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                        {orderActions.map((action) => {
                          const ActionIcon = actionIcons[action.key];
                          return (
                            <button
                              key={action.key}
                              onClick={() => setOpenMenuId(null)}
                              className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-foreground hover:bg-background/80"
                            >
                              <ActionIcon size={13} className="text-muted-light" />
                              {action.label}
                            </button>
                          );
                        })}
                      </div>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
