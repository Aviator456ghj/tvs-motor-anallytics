"use client";

import { useState } from "react";
import {
  ExternalLink,
  ChevronDown,
  Image as ImageIcon,
  Search,
  ListTree,
  BarChart3,
  History,
  PackageX,
  TrendingDown,
  AlertCircle,
  Wand2,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import {
  detailTabs,
  productVariants,
  activityLog,
  salesStats,
  seoFields,
  productAttributes,
  productAiInsightsDetail,
  salesChannelPublishState,
  type DetailTab,
  type Product,
  type ProductStatus,
} from "@/lib/products-data";

const statusBadge: Record<ProductStatus, string> = {
  Active: "bg-success-bg text-success",
  Draft: "bg-card-border/60 text-muted",
  "Out of Stock": "bg-danger-bg text-danger",
  "Low Stock": "bg-warning-bg text-warning",
  Discontinued: "bg-card-border/60 text-muted",
  Archived: "bg-card-border/60 text-muted",
};

const publishBadge: Record<string, string> = {
  Published: "bg-success-bg text-success",
  Hidden: "bg-card-border/60 text-muted",
  "Pending Approval": "bg-warning-bg text-warning",
};

const insightIconMap: Record<string, LucideIcon> = {
  "package-x": PackageX,
  "trending-down": TrendingDown,
  search: Search,
  image: ImageIcon,
  "alert-circle": AlertCircle,
};

const insightTone: Record<string, string> = {
  danger: "bg-danger-bg text-danger",
  warning: "bg-warning-bg text-warning",
  info: "bg-info-bg text-info",
};

export default function ProductDetailPanel({ product }: { product: Product }) {
  const [tab, setTab] = useState<DetailTab>("Overview");
  const margin = (((product.price - product.costPrice) / product.price) * 100).toFixed(2);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-card-border">
        <div className="flex items-center gap-2">
          <h3 className="text-[15px] font-semibold text-foreground">
            Product Details — {product.name} ({product.sku})
          </h3>
          <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${statusBadge[product.status]}`}>{product.status}</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">
            View Product <ExternalLink size={12} />
          </button>
          <button className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">
            More actions <ChevronDown size={13} />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1 px-5 pt-1 overflow-x-auto border-b border-card-border">
        {detailTabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`whitespace-nowrap px-2.5 py-2.5 text-[12.5px] font-medium border-b-2 -mb-px transition-colors ${
              tab === t ? "border-brand-start text-brand-start" : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="p-5">
        {tab === "Overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <div className="flex flex-col gap-1.5">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-1">Product Information</div>
              <div className="w-16 h-16 rounded-lg bg-background flex items-center justify-center mb-1">
                <ImageIcon size={22} className="text-muted-light" />
              </div>
              <Row label="Product Name" value={product.name} />
              <Row label="SKU" value={product.sku} />
              <Row label="Barcode" value={product.barcode} />
              <Row label="Category" value={product.category} />
              <Row label="Brand" value={product.brand} />
              <Row label="Product Type" value={product.type} />
              <Row label="Status" value={product.status} badge={statusBadge[product.status]} />
              <Row label="Created" value={product.created} />
              <Row label="Updated" value={product.updated} />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-1">Pricing</div>
              <Row label="Price" value={`$${product.price.toFixed(2)}`} />
              <Row label="Compare at Price" value={`$${product.compareAtPrice.toFixed(2)}`} />
              <Row label="Cost Price" value={`$${product.costPrice.toFixed(2)}`} />
              <Row label="Profit Margin" value={`${margin}%`} />
              <Row label="Currency" value={product.currency} />
              <Row label="Tax Class" value={product.taxClass} />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-1">Inventory</div>
              <Row label="Stock Quantity" value={String(product.stock)} />
              <Row label="Reserved" value={String(product.reserved)} />
              <Row label="Available" value={String(product.stock - product.reserved)} />
              <Row label="Warehouse" value={product.warehouse} />
              <Row label="Stock Status" value={product.status} badge={statusBadge[product.status]} />
              <Row label="Low Stock Threshold" value={String(product.lowStockThreshold)} />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-1">Sales Channels</div>
              {salesChannelPublishState.map((c) => (
                <div key={c.id} className="flex items-center justify-between text-[12.5px] py-0.5">
                  <span className="text-foreground">{c.label}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10.5px] font-medium ${publishBadge[c.status]}`}>{c.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "Variants" && (
          <div className="overflow-x-auto border border-card-border rounded-lg">
            <table className="w-full text-[12.5px] border-separate border-spacing-0">
              <thead>
                <tr className="text-left text-muted-light font-medium bg-background/60">
                  <th className="py-2 pl-3 pr-2 font-medium">Variant</th>
                  <th className="py-2 pr-2 font-medium">SKU</th>
                  <th className="py-2 pr-2 font-medium">Price</th>
                  <th className="py-2 pr-2 font-medium">Stock</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {productVariants.map((v) => (
                  <tr key={v.id} className="border-t border-card-border/70">
                    <td className="py-2.5 pl-3 pr-2 text-foreground">{v.name}</td>
                    <td className="py-2.5 pr-2 text-muted">{v.sku}</td>
                    <td className="py-2.5 pr-2 text-foreground font-medium">${v.price.toFixed(2)}</td>
                    <td className="py-2.5 pr-2 text-muted">{v.stock}</td>
                    <td className="py-2.5 pr-3">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${statusBadge[v.status]}`}>{v.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === "Inventory" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
            <Row label="Stock Quantity" value={String(product.stock)} />
            <Row label="Reserved" value={String(product.reserved)} />
            <Row label="Available" value={String(product.stock - product.reserved)} />
            <Row label="Warehouse" value={product.warehouse} />
            <Row label="Low Stock Threshold" value={String(product.lowStockThreshold)} />
            <Row label="Inventory Policy" value="Stop selling when out of stock" />
          </div>
        )}

        {tab === "Pricing" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
            <Row label="Price" value={`$${product.price.toFixed(2)}`} />
            <Row label="Compare at Price" value={`$${product.compareAtPrice.toFixed(2)}`} />
            <Row label="Cost Price" value={`$${product.costPrice.toFixed(2)}`} />
            <Row label="Profit Margin" value={`${margin}%`} />
            <Row label="Currency" value={product.currency} />
            <Row label="Tax Class" value={product.taxClass} />
          </div>
        )}

        {tab === "Media" && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="aspect-square rounded-lg bg-background flex items-center justify-center text-muted-light">
                <ImageIcon size={20} />
              </div>
            ))}
          </div>
        )}

        {tab === "SEO" && (
          <div className="flex flex-col gap-3 max-w-2xl">
            <Field label="SEO Title" value={seoFields.title} />
            <Field label="Meta Description" value={seoFields.description} multiline />
            <Field label="URL Handle" value={seoFields.handle} />
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-1.5">Keywords</div>
              <div className="flex flex-wrap gap-1.5">
                {seoFields.keywords.map((k) => (
                  <span key={k} className="px-2 py-1 rounded-full bg-background text-muted text-[11.5px]">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "Attributes" && (
          <div className="flex flex-col gap-1 max-w-md">
            {productAttributes.map((a) => (
              <div key={a.label} className="flex items-center justify-between text-[12.5px] py-1.5 border-b border-card-border/60 last:border-b-0">
                <span className="text-muted flex items-center gap-1.5">
                  <ListTree size={13} className="text-muted-light" />
                  {a.label}
                </span>
                <span className="text-foreground font-medium">{a.value}</span>
              </div>
            ))}
          </div>
        )}

        {tab === "Sales" && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {salesStats.map((s) => (
              <div key={s.label} className="rounded-lg bg-background p-3 flex flex-col gap-1">
                <span className="text-[11px] text-muted-light flex items-center gap-1">
                  <BarChart3 size={12} /> {s.label}
                </span>
                <span className="text-[17px] font-bold text-foreground">{s.value}</span>
              </div>
            ))}
          </div>
        )}

        {tab === "Activity" && (
          <div className="flex flex-col gap-3">
            {activityLog.map((a) => (
              <div key={a.id} className="flex items-start gap-2.5">
                <span className="w-7 h-7 rounded-full bg-background flex items-center justify-center text-muted-light shrink-0">
                  <History size={13} />
                </span>
                <div>
                  <div className="text-[12.5px] text-foreground">{a.text}</div>
                  <div className="text-[11px] text-muted-light">{a.actor} · {a.time}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "AI Insights" && (
          <div className="flex flex-col gap-3 max-w-xl">
            {productAiInsightsDetail.map((insight) => {
              const Icon = insightIconMap[insight.icon];
              return (
                <div key={insight.id} className="flex items-center gap-2.5">
                  <span className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${insightTone[insight.tone]}`}>
                    <Icon size={13} />
                  </span>
                  <span className="text-[12.5px] text-foreground">{insight.text}</span>
                </div>
              );
            })}
            <button className="mt-2 flex items-center gap-1.5 self-start rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white text-[12.5px] font-medium px-3.5 py-2 hover:opacity-90">
              <Wand2 size={13} />
              Generate AI Description
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}

function Row({ label, value, badge }: { label: string; value: string; badge?: string }) {
  return (
    <div className="flex items-center justify-between gap-2 text-[12.5px]">
      <span className="text-muted shrink-0">{label}</span>
      {badge ? (
        <span className={`px-2 py-0.5 rounded-full text-[10.5px] font-medium ${badge}`}>{value}</span>
      ) : (
        <span className="text-foreground font-medium text-right">{value}</span>
      )}
    </div>
  );
}

function Field({ label, value, multiline }: { label: string; value: string; multiline?: boolean }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-light mb-1.5">{label}</div>
      {multiline ? (
        <textarea
          defaultValue={value}
          rows={2}
          className="w-full rounded-lg border border-card-border bg-background/60 text-[12.5px] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-start/30"
        />
      ) : (
        <input
          defaultValue={value}
          className="w-full rounded-lg border border-card-border bg-background/60 text-[12.5px] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-start/30"
        />
      )}
    </div>
  );
}
