"use client";

import { useState } from "react";
import { MoreVertical, Package, CheckCircle2, Clock } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { orderDetail, itemRowActions } from "@/lib/order-detail-data";

export default function ItemsTable({ extended = false }: { extended?: boolean }) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const o = orderDetail;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-card-border">
        <h3 className="text-[14px] font-semibold text-foreground">Items ({o.items.length})</h3>
        <div className="flex items-center gap-2">
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Add Item</button>
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Edit Items</button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px] border-separate border-spacing-0">
          <thead>
            <tr className="text-left text-muted-light font-medium bg-background/60">
              <th className="py-2.5 pl-5 pr-2 font-medium">Product</th>
              <th className="py-2.5 pr-2 font-medium">SKU</th>
              <th className="py-2.5 pr-2 font-medium">Price</th>
              <th className="py-2.5 pr-2 font-medium">Qty</th>
              {extended && <th className="py-2.5 pr-2 font-medium">Reserved</th>}
              <th className="py-2.5 pr-2 font-medium">Fulfilled</th>
              {extended && <th className="py-2.5 pr-2 font-medium">Returned</th>}
              <th className="py-2.5 pr-2 font-medium text-right">Total</th>
              <th className="py-2.5 pr-5 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {o.items.map((item) => (
              <tr key={item.id} className="border-t border-card-border/70">
                <td className="py-3 pl-5 pr-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                      <Package size={15} />
                    </span>
                    <div>
                      <div className="text-foreground font-medium whitespace-nowrap">{item.name}</div>
                      <div className="text-muted-light text-[11.5px] whitespace-nowrap">{item.variant}</div>
                    </div>
                  </div>
                </td>
                <td className="py-3 pr-2 text-muted whitespace-nowrap">{item.sku}</td>
                <td className="py-3 pr-2 text-foreground whitespace-nowrap">${item.price.toFixed(2)}</td>
                <td className="py-3 pr-2 text-foreground whitespace-nowrap">{item.qty}</td>
                {extended && <td className="py-3 pr-2 text-muted whitespace-nowrap">{item.reserved}</td>}
                <td className="py-3 pr-2">
                  {item.fulfilled >= item.qty ? (
                    <span className="flex items-center gap-1 text-success text-[12px] font-medium whitespace-nowrap">
                      <CheckCircle2 size={13} /> {item.fulfilled}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-warning text-[12px] font-medium whitespace-nowrap">
                      <Clock size={13} /> Pending
                    </span>
                  )}
                </td>
                {extended && <td className="py-3 pr-2 text-muted whitespace-nowrap">{item.returned}</td>}
                <td className="py-3 pr-2 text-foreground font-medium text-right whitespace-nowrap">${item.total.toFixed(2)}</td>
                <td className="py-3 pr-5 text-right relative">
                  <button
                    onClick={() => setOpenMenuId((v) => (v === item.id ? null : item.id))}
                    className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80"
                  >
                    <MoreVertical size={14} />
                  </button>
                  {openMenuId === item.id && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
                      <div className="absolute right-5 top-full mt-1 w-40 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                        {itemRowActions.map((a) => (
                          <button
                            key={a}
                            onClick={() => setOpenMenuId(null)}
                            className={`w-full text-left px-3 py-1.5 text-[12px] hover:bg-background/80 ${a === "Remove Item" ? "text-danger" : "text-foreground"}`}
                          >
                            {a}
                          </button>
                        ))}
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
