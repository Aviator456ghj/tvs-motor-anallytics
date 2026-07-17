"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye, MoreVertical, Check, X, Tag, PackageCheck, FlaskConical } from "lucide-react";
import { statusStyle, reasonStyle, returnRowActions, type ReturnRequest } from "@/lib/returns-data";

const actionIcons: Record<string, typeof Eye> = {
  view: Eye,
  approve: Check,
  reject: X,
  label: Tag,
  received: PackageCheck,
  inspection: FlaskConical,
};

export default function ReturnsTable({
  rows,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onView,
  currentPage,
  totalPages,
  onPageChange,
  totalCount,
}: {
  rows: ReturnRequest[];
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

  return (
    <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px] border-separate border-spacing-0">
          <thead>
            <tr className="text-left text-muted-light font-medium bg-background/60">
              <th className="py-2.5 pl-4 pr-2 w-8">
                <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} className="accent-brand-start" />
              </th>
              <th className="py-2.5 pr-3 font-medium">RMA ID</th>
              <th className="py-2.5 pr-3 font-medium">Order ID</th>
              <th className="py-2.5 pr-3 font-medium">Customer</th>
              <th className="py-2.5 pr-3 font-medium">Items</th>
              <th className="py-2.5 pr-3 font-medium">Reason</th>
              <th className="py-2.5 pr-3 font-medium">Status</th>
              <th className="py-2.5 pr-3 font-medium">Return Type</th>
              <th className="py-2.5 pr-3 font-medium">Requested On</th>
              <th className="py-2.5 pr-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-card-border/70 hover:bg-background/40">
                <td className="py-2.5 pl-4 pr-2">
                  <input type="checkbox" checked={selectedIds.has(r.id)} onChange={() => onToggleSelect(r.id)} className="accent-brand-start" />
                </td>
                <td className="py-2.5 pr-3 whitespace-nowrap">
                  <button onClick={() => onView(r.id)} className="text-brand-start font-medium hover:underline">
                    {r.id}
                  </button>
                  <div className="text-[11px] text-muted-light">{r.requestedOn}</div>
                </td>
                <td className="py-2.5 pr-3 whitespace-nowrap">
                  <Link href={`/orders/${r.orderId.replace("#", "")}`} className="text-brand-start hover:underline">
                    {r.orderId}
                  </Link>
                </td>
                <td className="py-2.5 pr-3 whitespace-nowrap">
                  <div className="text-foreground font-medium">{r.customer}</div>
                  <div className="text-[11px] text-muted-light">{r.email}</div>
                </td>
                <td className="py-2.5 pr-3 text-muted whitespace-nowrap">
                  {r.items} Items
                  <div className="text-[11px] text-muted-light">SKU: {r.sku}</div>
                </td>
                <td className="py-2.5 pr-3">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${reasonStyle[r.reason]}`}>{r.reason}</span>
                </td>
                <td className="py-2.5 pr-3">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${statusStyle[r.status]}`}>{r.status}</span>
                </td>
                <td className="py-2.5 pr-3 text-muted whitespace-nowrap">{r.returnType}</td>
                <td className="py-2.5 pr-3 text-muted-light whitespace-nowrap">{r.requestedOn}</td>
                <td className="py-2.5 pr-4 text-right relative">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => onView(r.id)} className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80" title="View">
                      <Eye size={14} />
                    </button>
                    <button
                      onClick={() => setOpenMenuId((v) => (v === r.id ? null : r.id))}
                      className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80"
                    >
                      <MoreVertical size={14} />
                    </button>
                  </div>
                  {openMenuId === r.id && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
                      <div className="absolute right-4 top-full mt-1 w-48 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                        {returnRowActions.map((a) => {
                          const Icon = actionIcons[a.key];
                          const danger = "danger" in a && a.danger;
                          return (
                            <button
                              key={a.key}
                              onClick={() => {
                                setOpenMenuId(null);
                                if (a.key === "view") onView(r.id);
                              }}
                              className={`w-full flex items-center gap-2 px-3 py-1.5 text-[12px] hover:bg-background/80 ${danger ? "text-danger" : "text-foreground"}`}
                            >
                              <Icon size={13} className={danger ? "text-danger" : "text-muted-light"} />
                              {a.label}
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
