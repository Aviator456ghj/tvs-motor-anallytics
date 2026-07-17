"use client";

import { useState } from "react";
import { Headphones, Watch, Shirt, Backpack, Footprints, Sofa, Eye, Pencil, MoreHorizontal, Copy, Boxes, BarChart3, Archive, Trash2, Monitor, type LucideIcon } from "lucide-react";
import type { Product, ProductColumnKey, ProductStatus } from "@/lib/products-data";

const productIcons: Record<string, LucideIcon> = {
  "1": Headphones,
  "2": Watch,
  "3": Shirt,
  "4": Backpack,
  "5": Footprints,
  "6": Sofa,
};

const statusBadge: Record<ProductStatus, string> = {
  Active: "bg-success-bg text-success",
  Draft: "bg-card-border/60 text-muted",
  "Out of Stock": "bg-danger-bg text-danger",
  "Low Stock": "bg-warning-bg text-warning",
  Discontinued: "bg-card-border/60 text-muted",
  Archived: "bg-card-border/60 text-muted",
};

const typeBadge: Record<string, string> = {
  Simple: "bg-background text-muted",
  Variant: "bg-indigo-50 text-indigo-600",
  Digital: "bg-blue-50 text-blue-600",
  Bundle: "bg-violet-50 text-violet-600",
  Subscription: "bg-cyan-50 text-cyan-600",
  "Gift Card": "bg-rose-50 text-rose-600",
  Service: "bg-teal-50 text-teal-600",
};

const channelBadge: Record<string, { label: string; className: string } | { icon: LucideIcon; className: string }> = {
  "online-store": { icon: Monitor, className: "bg-background text-muted" },
  amazon: { label: "a", className: "bg-[#FF9900] text-white" },
  facebook: { label: "f", className: "bg-[#1877F2] text-white" },
  tiktok: { label: "t", className: "bg-black text-white" },
};

const rowActions = [
  { key: "duplicate", label: "Duplicate", icon: Copy },
  { key: "manage-inventory", label: "Manage Inventory", icon: Boxes },
  { key: "analytics", label: "Analytics", icon: BarChart3 },
  { key: "archive", label: "Archive", icon: Archive },
  { key: "delete", label: "Delete", icon: Trash2 },
] as const;

export default function ProductsTable({
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
  rows: Product[];
  visibleColumns: Set<ProductColumnKey>;
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
  const col = (key: ProductColumnKey) => visibleColumns.has(key);

  return (
    <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px] border-separate border-spacing-0">
          <thead>
            <tr className="text-left text-muted-light font-medium bg-background/60">
              <th className="py-2.5 pl-4 pr-2 w-8">
                <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} className="accent-brand-start" />
              </th>
              <th className="py-2.5 pr-3 font-medium">Product</th>
              <th className="py-2.5 pr-3 font-medium">SKU</th>
              {col("category") && <th className="py-2.5 pr-3 font-medium">Category</th>}
              {col("price") && <th className="py-2.5 pr-3 font-medium">Price</th>}
              {col("stock") && <th className="py-2.5 pr-3 font-medium">Stock</th>}
              {col("status") && <th className="py-2.5 pr-3 font-medium">Status</th>}
              {col("type") && <th className="py-2.5 pr-3 font-medium">Type</th>}
              {col("channels") && <th className="py-2.5 pr-3 font-medium">Sales Channel</th>}
              {col("created") && <th className="py-2.5 pr-3 font-medium">Created</th>}
              {col("updated") && <th className="py-2.5 pr-3 font-medium">Updated</th>}
              <th className="py-2.5 pr-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const Icon = productIcons[p.id] ?? Boxes;
              const shownChannels = p.channels.slice(0, 3);
              const extra = p.channels.length - shownChannels.length;
              return (
                <tr key={p.id} className="border-t border-card-border/70 hover:bg-background/40">
                  <td className="py-2.5 pl-4 pr-2">
                    <input type="checkbox" checked={selectedIds.has(p.id)} onChange={() => onToggleSelect(p.id)} className="accent-brand-start" />
                  </td>
                  <td className="py-2.5 pr-3">
                    <button onClick={() => onView(p.id)} className="flex items-center gap-2.5 text-left hover:underline">
                      <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                        <Icon size={16} />
                      </span>
                      <span>
                        <div className="text-foreground font-medium whitespace-nowrap">{p.name}</div>
                        <div className="text-muted-light text-[11.5px] whitespace-nowrap">{p.variant}</div>
                      </span>
                    </button>
                  </td>
                  <td className="py-2.5 pr-3 text-muted whitespace-nowrap">{p.sku}</td>
                  {col("category") && <td className="py-2.5 pr-3 text-muted whitespace-nowrap">{p.category.split(" > ")[0]}</td>}
                  {col("price") && <td className="py-2.5 pr-3 text-foreground font-medium whitespace-nowrap">${p.price.toFixed(2)}</td>}
                  {col("stock") && (
                    <td className={`py-2.5 pr-3 font-medium whitespace-nowrap ${p.stock === 0 ? "text-danger" : p.stock <= p.lowStockThreshold ? "text-warning" : "text-success"}`}>
                      {p.stock}
                    </td>
                  )}
                  {col("status") && (
                    <td className="py-2.5 pr-3">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${statusBadge[p.status]}`}>{p.status}</span>
                    </td>
                  )}
                  {col("type") && (
                    <td className="py-2.5 pr-3">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${typeBadge[p.type]}`}>{p.type}</span>
                    </td>
                  )}
                  {col("channels") && (
                    <td className="py-2.5 pr-3">
                      <div className="flex items-center gap-1">
                        {shownChannels.map((c) => {
                          const badge = channelBadge[c];
                          if (!badge) return null;
                          if ("icon" in badge) {
                            const ChIcon = badge.icon;
                            return (
                              <span key={c} className={`w-5 h-5 rounded flex items-center justify-center ${badge.className}`}>
                                <ChIcon size={11} />
                              </span>
                            );
                          }
                          return (
                            <span key={c} className={`w-5 h-5 rounded flex items-center justify-center text-[9.5px] font-bold ${badge.className}`}>
                              {badge.label}
                            </span>
                          );
                        })}
                        {extra > 0 && <span className="text-[11px] text-muted-light">+{extra}</span>}
                      </div>
                    </td>
                  )}
                  {col("created") && <td className="py-2.5 pr-3 text-muted-light whitespace-nowrap">{p.created}</td>}
                  {col("updated") && <td className="py-2.5 pr-3 text-muted-light whitespace-nowrap">{p.updated}</td>}
                  <td className="py-2.5 pr-4 text-right relative">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => onView(p.id)} className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80" title="View">
                        <Eye size={14} />
                      </button>
                      <button className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80" title="Edit">
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => setOpenMenuId((v) => (v === p.id ? null : p.id))}
                        className="w-6 h-6 inline-flex items-center justify-center rounded-md text-muted-light hover:bg-background/80"
                      >
                        <MoreHorizontal size={15} />
                      </button>
                    </div>
                    {openMenuId === p.id && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
                        <div className="absolute right-4 top-full mt-1 w-48 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
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
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-4 py-3 border-t border-card-border text-[12.5px]">
        <span className="text-muted-light">
          Showing {(currentPage - 1) * 6 + 1} to {Math.min(currentPage * 6, totalCount)} of {totalCount.toLocaleString()} products
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
