"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye, Pencil, MoreHorizontal, Copy, RotateCcw, XCircle, Archive, Trash2, History, ShieldAlert } from "lucide-react";
import type { Order, OrderColumnKey, PaymentStatus, FulfillmentStatus } from "@/lib/orders-data";

const paymentBadge: Record<PaymentStatus, string> = {
  Paid: "bg-success-bg text-success",
  Pending: "bg-warning-bg text-warning",
  "Partially Paid": "bg-orange-50 text-orange-600",
  Refunded: "bg-info-bg text-info",
  Voided: "bg-card-border/60 text-muted",
};

const fulfillmentBadge: Record<FulfillmentStatus, string> = {
  Unfulfilled: "bg-warning-bg text-warning",
  "Partially Fulfilled": "bg-orange-50 text-orange-600",
  Fulfilled: "bg-success-bg text-success",
  Backordered: "bg-danger-bg text-danger",
};

const riskBadge: Record<Order["risk"], string> = {
  Low: "text-success",
  Medium: "text-warning",
  High: "text-danger",
};

const rowActions = [
  { key: "duplicate", label: "Duplicate", icon: Copy },
  { key: "refund", label: "Refund", icon: RotateCcw },
  { key: "cancel", label: "Cancel", icon: XCircle },
  { key: "archive", label: "Archive", icon: Archive },
  { key: "delete", label: "Delete", icon: Trash2 },
  { key: "timeline", label: "Timeline", icon: History },
  { key: "audit", label: "Audit Logs", icon: ShieldAlert },
] as const;

export default function OrdersTable({
  rows,
  visibleColumns,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onView,
  currentPage,
  totalPages,
  onPageChange,
  totalCount,
}: {
  rows: Order[];
  visibleColumns: Set<OrderColumnKey>;
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  onView: (id: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalCount: number;
}) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const allSelected = rows.length > 0 && rows.every((r) => selectedIds.has(r.id));

  const col = (key: OrderColumnKey) => visibleColumns.has(key);

  return (
    <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px] border-separate border-spacing-0">
          <thead>
            <tr className="text-left text-muted-light font-medium bg-background/60">
              <th className="py-2.5 pl-4 pr-2 w-8">
                <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} className="accent-brand-start" />
              </th>
              <th className="py-2.5 pr-3 font-medium">Order</th>
              <th className="py-2.5 pr-3 font-medium">Date</th>
              {col("customer") && <th className="py-2.5 pr-3 font-medium">Customer</th>}
              {col("channel") && <th className="py-2.5 pr-3 font-medium">Channel</th>}
              {col("items") && <th className="py-2.5 pr-3 font-medium">Items</th>}
              {col("subtotal") && <th className="py-2.5 pr-3 font-medium">Subtotal</th>}
              {col("discount") && <th className="py-2.5 pr-3 font-medium">Discount</th>}
              {col("shipping") && <th className="py-2.5 pr-3 font-medium">Shipping</th>}
              {col("tax") && <th className="py-2.5 pr-3 font-medium">Tax</th>}
              {col("total") && <th className="py-2.5 pr-3 font-medium">Total</th>}
              {col("payment") && <th className="py-2.5 pr-3 font-medium">Payment</th>}
              {col("fulfillment") && <th className="py-2.5 pr-3 font-medium">Fulfillment</th>}
              {col("risk") && <th className="py-2.5 pr-3 font-medium">Risk</th>}
              {col("tags") && <th className="py-2.5 pr-3 font-medium">Tags</th>}
              <th className="py-2.5 pr-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((order) => (
              <tr key={order.id} className="border-t border-card-border/70 hover:bg-background/40">
                <td className="py-2.5 pl-4 pr-2">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(order.id)}
                    onChange={() => onToggleSelect(order.id)}
                    className="accent-brand-start"
                  />
                </td>
                <td className="py-2.5 pr-3 font-medium text-brand-start whitespace-nowrap">
                  <Link href={`/orders/${order.id.replace("#", "")}`} className="hover:underline">
                    {order.id}
                  </Link>
                </td>
                <td className="py-2.5 pr-3 text-muted-light whitespace-nowrap">{order.date}</td>
                {col("customer") && <td className="py-2.5 pr-3 text-foreground whitespace-nowrap">{order.customer}</td>}
                {col("channel") && <td className="py-2.5 pr-3 text-muted whitespace-nowrap">{order.channel}</td>}
                {col("items") && <td className="py-2.5 pr-3 text-muted whitespace-nowrap">{order.items} item{order.items > 1 ? "s" : ""}</td>}
                {col("subtotal") && <td className="py-2.5 pr-3 text-muted whitespace-nowrap">${order.subtotal.toFixed(2)}</td>}
                {col("discount") && <td className="py-2.5 pr-3 text-muted whitespace-nowrap">${order.discount.toFixed(2)}</td>}
                {col("shipping") && <td className="py-2.5 pr-3 text-muted whitespace-nowrap">${order.shipping.toFixed(2)}</td>}
                {col("tax") && <td className="py-2.5 pr-3 text-muted whitespace-nowrap">${order.tax.toFixed(2)}</td>}
                {col("total") && <td className="py-2.5 pr-3 text-foreground font-medium whitespace-nowrap">${order.total.toFixed(2)}</td>}
                {col("payment") && (
                  <td className="py-2.5 pr-3">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${paymentBadge[order.payment]}`}>
                      {order.payment}
                    </span>
                  </td>
                )}
                {col("fulfillment") && (
                  <td className="py-2.5 pr-3">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${fulfillmentBadge[order.fulfillment]}`}>
                      {order.fulfillment}
                    </span>
                  </td>
                )}
                {col("risk") && (
                  <td className={`py-2.5 pr-3 text-[11.5px] font-medium whitespace-nowrap ${riskBadge[order.risk]}`}>{order.risk}</td>
                )}
                {col("tags") && (
                  <td className="py-2.5 pr-3 whitespace-nowrap">
                    {order.tags.length === 0 ? (
                      <span className="text-muted-light">—</span>
                    ) : (
                      order.tags.map((t) => (
                        <span key={t} className="inline-block mr-1 px-1.5 py-0.5 rounded bg-background text-muted text-[10.5px]">
                          {t}
                        </span>
                      ))
                    )}
                  </td>
                )}
                <td className="py-2.5 pr-4 text-right relative">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => onView(order.id)} className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80" title="View">
                      <Eye size={14} />
                    </button>
                    <button className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80" title="Edit">
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => setOpenMenuId((v) => (v === order.id ? null : order.id))}
                      className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80"
                    >
                      <MoreHorizontal size={15} />
                    </button>
                  </div>
                  {openMenuId === order.id && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
                      <div className="absolute right-4 top-full mt-1 w-40 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                        {rowActions.map((a) => (
                          <button
                            key={a.key}
                            onClick={() => setOpenMenuId(null)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-foreground hover:bg-background/80"
                          >
                            <a.icon size={13} className="text-muted-light" />
                            {a.label}
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

      <div className="flex items-center justify-between px-4 py-3 border-t border-card-border text-[12.5px]">
        <span className="text-muted-light">
          Showing {(currentPage - 1) * 8 + 1} to {Math.min(currentPage * 8, totalCount)} of {totalCount.toLocaleString()} orders
        </span>
        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`w-7 h-7 rounded-md text-[12px] font-medium ${
                p === currentPage ? "bg-brand-start text-white" : "text-muted hover:bg-background/80"
              }`}
            >
              {p}
            </button>
          ))}
          <span className="px-1 text-muted-light">…</span>
          <button
            onClick={() => onPageChange(totalPages)}
            className="w-7 h-7 rounded-md text-[12px] font-medium text-muted hover:bg-background/80"
          >
            {totalPages}
          </button>
          <button
            onClick={() => onPageChange(Math.min(currentPage + 1, totalPages))}
            className="w-7 h-7 rounded-md text-muted hover:bg-background/80 flex items-center justify-center"
          >
            »
          </button>
        </div>
      </div>
    </div>
  );
}
