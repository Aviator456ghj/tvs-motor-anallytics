"use client";

import { useState } from "react";
import { Search, Minus, Plus, Trash2, Package } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { orderableProducts, inventoryStatusFor, type OrderableProduct } from "@/lib/create-order-data";

export type LineItem = { productId: string; qty: number };

const statusStyle: Record<string, string> = {
  "In Stock": "bg-success-bg text-success",
  "Low Stock": "bg-warning-bg text-warning",
  "Out of Stock": "bg-danger-bg text-danger",
};

export default function StepProducts({
  lineItems,
  onAdd,
  onUpdateQty,
  onRemove,
}: {
  lineItems: LineItem[];
  onAdd: (productId: string) => void;
  onUpdateQty: (productId: string, qty: number) => void;
  onRemove: (productId: string) => void;
}) {
  const [query, setQuery] = useState("");

  const results = query.trim()
    ? orderableProducts.filter(
        (p) => p.name.toLowerCase().includes(query.toLowerCase()) || p.sku.toLowerCase().includes(query.toLowerCase())
      )
    : orderableProducts;

  return (
    <div className="flex flex-col gap-4">
      <Card className="p-5">
        <h3 className="text-[14.5px] font-semibold text-foreground mb-3">Add Products</h3>
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-light" size={15} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search products by name or SKU..."
            className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-card-border bg-background/60 text-[13px] placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30"
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {results.map((p) => {
            const status = inventoryStatusFor(p.stock);
            const inCart = lineItems.some((li) => li.productId === p.id);
            return (
              <div key={p.id} className="flex items-center gap-2.5 rounded-lg border border-card-border p-2.5">
                <span className="w-9 h-9 rounded-lg bg-background flex items-center justify-center text-muted shrink-0">
                  <Package size={15} />
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-[12.5px] font-medium text-foreground truncate">{p.name}</div>
                  <div className="text-[11px] text-muted-light">${p.price.toFixed(2)} · {p.sku}</div>
                </div>
                <button
                  onClick={() => onAdd(p.id)}
                  disabled={status === "Out of Stock" || inCart}
                  className="text-[11.5px] font-medium text-white bg-brand-start rounded-lg px-2.5 py-1.5 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                >
                  {inCart ? "Added" : "Add"}
                </button>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="px-5 py-4 border-b border-card-border">
          <h3 className="text-[14.5px] font-semibold text-foreground">Order Items ({lineItems.length})</h3>
        </div>
        {lineItems.length === 0 ? (
          <div className="px-5 py-10 text-center text-[13px] text-muted-light">No items added yet — search and add products above.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[12.5px] border-separate border-spacing-0">
              <thead>
                <tr className="text-left text-muted-light font-medium bg-background/60">
                  <th className="py-2 pl-5 pr-2 font-medium">Product</th>
                  <th className="py-2 pr-2 font-medium">SKU</th>
                  <th className="py-2 pr-2 font-medium">Price</th>
                  <th className="py-2 pr-2 font-medium">Qty</th>
                  <th className="py-2 pr-2 font-medium">Inventory</th>
                  <th className="py-2 pr-2 font-medium text-right">Total</th>
                  <th className="py-2 pr-5 font-medium text-right">Remove</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((li) => {
                  const p = orderableProducts.find((x) => x.id === li.productId) as OrderableProduct;
                  const status = inventoryStatusFor(p.stock);
                  return (
                    <tr key={li.productId} className="border-t border-card-border/70">
                      <td className="py-2.5 pl-5 pr-2">
                        <div className="text-foreground font-medium whitespace-nowrap">{p.name}</div>
                        <div className="text-muted-light text-[11px] whitespace-nowrap">{p.variant}</div>
                      </td>
                      <td className="py-2.5 pr-2 text-muted whitespace-nowrap">{p.sku}</td>
                      <td className="py-2.5 pr-2 text-foreground whitespace-nowrap">${p.price.toFixed(2)}</td>
                      <td className="py-2.5 pr-2">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => onUpdateQty(li.productId, Math.max(1, li.qty - 1))}
                            className="w-6 h-6 flex items-center justify-center rounded border border-card-border text-muted hover:bg-background/80"
                          >
                            <Minus size={11} />
                          </button>
                          <span className="w-7 text-center">{li.qty}</span>
                          <button
                            onClick={() => onUpdateQty(li.productId, li.qty + 1)}
                            className="w-6 h-6 flex items-center justify-center rounded border border-card-border text-muted hover:bg-background/80"
                          >
                            <Plus size={11} />
                          </button>
                        </div>
                      </td>
                      <td className="py-2.5 pr-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10.5px] font-medium whitespace-nowrap ${statusStyle[status]}`}>{status}</span>
                      </td>
                      <td className="py-2.5 pr-2 text-foreground font-medium text-right whitespace-nowrap">${(p.price * li.qty).toFixed(2)}</td>
                      <td className="py-2.5 pr-5 text-right">
                        <button onClick={() => onRemove(li.productId)} className="text-muted-light hover:text-danger">
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
