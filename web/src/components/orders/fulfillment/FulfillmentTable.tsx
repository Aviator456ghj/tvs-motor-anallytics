"use client";

import { useState } from "react";
import Link from "next/link";
import { Clipboard, Printer, MoreVertical, UserPlus, PackageCheck, Ban } from "lucide-react";
import { statusStyle, priorityStyle, type FulfillmentOrder } from "@/lib/fulfillment-data";

const rowActions = [
  { key: "assign", label: "Assign Picker", icon: UserPlus },
  { key: "mark-picked", label: "Mark Picked", icon: PackageCheck },
  { key: "hold", label: "Put On Hold", icon: Ban },
];

export default function FulfillmentTable({
  rows,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  currentPage,
  totalPages,
  onPageChange,
  totalCount,
}: {
  rows: FulfillmentOrder[];
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalCount: number;
}) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const allSelected = rows.length > 0 && rows.every((r) => selectedIds.has(r.id));

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
              <th className="py-2.5 pr-3 font-medium">Customer</th>
              <th className="py-2.5 pr-3 font-medium">Items</th>
              <th className="py-2.5 pr-3 font-medium">Warehouse</th>
              <th className="py-2.5 pr-3 font-medium">Status</th>
              <th className="py-2.5 pr-3 font-medium">Priority</th>
              <th className="py-2.5 pr-3 font-medium">Shipping Method</th>
              <th className="py-2.5 pr-3 font-medium">Ship By</th>
              <th className="py-2.5 pr-3 font-medium">Picker / Packer</th>
              <th className="py-2.5 pr-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.id} className="border-t border-card-border/70 hover:bg-background/40">
                <td className="py-2.5 pl-4 pr-2">
                  <input type="checkbox" checked={selectedIds.has(o.id)} onChange={() => onToggleSelect(o.id)} className="accent-brand-start" />
                </td>
                <td className="py-2.5 pr-3 whitespace-nowrap">
                  <Link href={`/orders/${o.id.replace("#", "")}`} className="text-brand-start font-medium hover:underline">
                    {o.id}
                  </Link>
                </td>
                <td className="py-2.5 pr-3 whitespace-nowrap">
                  <div className="text-foreground font-medium">{o.customer}</div>
                  <div className="text-[11px] text-muted-light">{o.email}</div>
                </td>
                <td className="py-2.5 pr-3 text-muted whitespace-nowrap">
                  {o.items} Items
                  <div className="text-[11px] text-muted-light">SKU: {o.sku}</div>
                </td>
                <td className="py-2.5 pr-3 whitespace-nowrap">
                  <span className="flex items-center gap-1.5">
                    <span className="w-6 h-6 rounded bg-background flex items-center justify-center text-[9.5px] font-bold text-muted">{o.warehouseCode}</span>
                    <span className="text-muted">{o.warehouse}</span>
                  </span>
                </td>
                <td className="py-2.5 pr-3">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${statusStyle[o.status]}`}>{o.status}</span>
                  {o.expedited && (
                    <div className="mt-1">
                      <span className="px-1.5 py-0.5 rounded bg-danger-bg text-danger text-[10px] font-medium">Expedited</span>
                    </div>
                  )}
                </td>
                <td className={`py-2.5 pr-3 text-[12px] font-medium whitespace-nowrap ${priorityStyle[o.priority]}`}>
                  {o.priority === "High" ? "↑" : o.priority === "Low" ? "↓" : "•"} {o.priority}
                </td>
                <td className="py-2.5 pr-3 text-muted whitespace-nowrap">{o.shippingMethod}</td>
                <td className="py-2.5 pr-3 text-muted-light whitespace-nowrap">{o.shipBy}</td>
                <td className="py-2.5 pr-3 text-muted-light whitespace-nowrap">
                  {o.picker ?? <span className="italic">Unassigned</span>}
                </td>
                <td className="py-2.5 pr-4 text-right relative">
                  <div className="flex items-center justify-end gap-1">
                    <button className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80" title="Print pick list">
                      <Clipboard size={14} />
                    </button>
                    <button className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80" title="Print label">
                      <Printer size={14} />
                    </button>
                    <button
                      onClick={() => setOpenMenuId((v) => (v === o.id ? null : o.id))}
                      className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80"
                    >
                      <MoreVertical size={14} />
                    </button>
                  </div>
                  {openMenuId === o.id && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
                      <div className="absolute right-4 top-full mt-1 w-44 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
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
          Showing {(currentPage - 1) * 5 + 1} to {Math.min(currentPage * 5, totalCount)} of {totalCount.toLocaleString()} entries
        </span>
        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`w-7 h-7 rounded-md text-[12px] font-medium ${p === currentPage ? "bg-brand-start text-white" : "text-muted hover:bg-background/80"}`}
            >
              {p}
            </button>
          ))}
          <span className="px-1 text-muted-light">…</span>
          <button onClick={() => onPageChange(totalPages)} className="w-7 h-7 rounded-md text-[12px] font-medium text-muted hover:bg-background/80">
            {totalPages}
          </button>
          <button onClick={() => onPageChange(Math.min(currentPage + 1, totalPages))} className="w-7 h-7 rounded-md text-muted hover:bg-background/80 flex items-center justify-center">
            »
          </button>
        </div>
      </div>
    </div>
  );
}
