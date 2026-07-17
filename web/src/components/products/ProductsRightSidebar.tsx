"use client";

import { useState } from "react";
import {
  PlusSquare,
  Upload,
  Download,
  ListChecks,
  Layers,
  Award,
  ListTree,
  Star,
  Trash,
  ChevronRight,
  X,
  Sparkles,
  PackageX,
  TrendingUp,
  Search,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { quickActions, productStatusLegend, topCategories, aiInsights } from "@/lib/products-data";

const iconMap: Record<string, LucideIcon> = {
  "plus-square": PlusSquare,
  upload: Upload,
  download: Download,
  "list-checks": ListChecks,
  layers: Layers,
  award: Award,
  "list-tree": ListTree,
  star: Star,
  trash: Trash,
};

const insightIconMap: Record<string, LucideIcon> = {
  "package-x": PackageX,
  "trending-up": TrendingUp,
  search: Search,
};

export default function ProductsRightSidebar() {
  const [insightsOpen, setInsightsOpen] = useState(true);

  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Quick Actions</h3>
        <div className="flex flex-col gap-1">
          {quickActions.map((action) => {
            const Icon = iconMap[action.icon];
            return (
              <button key={action.id} className="flex items-center gap-2.5 rounded-lg px-2 py-2 text-[12.5px] font-medium text-foreground hover:bg-background/80 text-left">
                <span className="w-7 h-7 rounded-lg bg-background flex items-center justify-center text-brand-start shrink-0">
                  <Icon size={14} />
                </span>
                {action.label}
              </button>
            );
          })}
        </div>
      </Card>

      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Product Status</h3>
        <div className="flex flex-col gap-2.5">
          {productStatusLegend.map((s) => (
            <div key={s.label} className="flex items-center gap-2.5">
              <span className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
              <span className="text-[12.5px] font-medium text-foreground w-[92px] shrink-0">{s.label}</span>
              <span className="text-[11.5px] text-muted-light">{s.description}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h3 className="text-[13.5px] font-semibold text-foreground mb-3">Top Categories</h3>
        <div className="flex flex-col gap-1">
          {topCategories.map((c) => (
            <button key={c.id} className="flex items-center justify-between rounded-lg px-2 py-1.5 text-[12.5px] hover:bg-background/80">
              <span className="text-foreground">{c.name}</span>
              <span className="text-muted-light">{c.count.toLocaleString()}</span>
            </button>
          ))}
          <button className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline mt-1 px-2">
            View all categories <ChevronRight size={12} />
          </button>
        </div>
      </Card>

      {insightsOpen && (
        <Card className="p-4 bg-gradient-to-br from-brand-start/[0.06] to-brand-end/[0.06] border-brand-start/20">
          <div className="flex items-center justify-between mb-2.5">
            <h3 className="text-[13.5px] font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles size={14} className="text-brand-start" /> AI Insights
            </h3>
            <button onClick={() => setInsightsOpen(false)} className="text-muted-light hover:text-muted">
              <X size={14} />
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {aiInsights.map((insight) => {
              const Icon = insightIconMap[insight.icon];
              return (
                <div key={insight.id} className="flex items-center gap-2 text-[12px] text-foreground">
                  <Icon size={13} className="text-brand-start shrink-0" />
                  {insight.text}
                </div>
              );
            })}
          </div>
          <button className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline mt-2.5">
            View all insights <ChevronRight size={12} />
          </button>
        </Card>
      )}
    </div>
  );
}
