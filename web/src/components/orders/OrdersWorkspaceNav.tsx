"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  ShoppingBag,
  LayoutDashboard,
  PlusSquare,
  FileText,
  Truck,
  RotateCcw,
  Banknote,
  FileEdit,
  ListChecks,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { ordersNavItems } from "@/lib/orders-nav";

const iconMap: Record<string, LucideIcon> = {
  "layout-dashboard": LayoutDashboard,
  "plus-square": PlusSquare,
  "file-text": FileText,
  truck: Truck,
  "rotate-ccw": RotateCcw,
  banknote: Banknote,
  "file-edit": FileEdit,
  "list-checks": ListChecks,
  settings: Settings,
};

const reservedSegments = ["create", "fulfillment", "returns", "refunds", "drafts", "bulk", "settings"];

function activeKeyFor(pathname: string): string {
  if (pathname === "/orders") return "dashboard";
  const parts = pathname.split("/").filter(Boolean); // ["orders", "<segment>", ...]
  const segment = parts[1];
  if (!segment) return "dashboard";
  if (reservedSegments.includes(segment)) {
    const map: Record<string, string> = {
      create: "create",
      fulfillment: "fulfillment",
      returns: "returns",
      refunds: "refunds",
      drafts: "drafts",
      bulk: "bulk",
      settings: "settings",
    };
    return map[segment];
  }
  return "details";
}

export default function OrdersWorkspaceNav() {
  const pathname = usePathname();
  const activeKey = activeKeyFor(pathname);

  return (
    <div className="bg-card-bg border border-card-border rounded-xl px-4 py-2.5 flex items-center gap-4 overflow-x-auto">
      <span className="flex items-center gap-1.5 text-[12.5px] font-semibold text-foreground shrink-0 pr-3 border-r border-card-border">
        <ShoppingBag size={14} className="text-brand-start" />
        Orders
      </span>
      <div className="flex items-center gap-4 shrink-0">
        {ordersNavItems.map((item) => {
          const Icon = iconMap[item.icon];
          const active = item.key === activeKey;
          return (
            <Link
              key={item.key}
              href={item.href}
              className={`flex items-center gap-1.5 text-[12.5px] font-medium whitespace-nowrap pb-1.5 pt-0.5 border-b-2 -mb-px transition-colors ${
                active
                  ? "border-brand-start text-brand-start"
                  : "border-transparent text-muted hover:text-foreground"
              }`}
            >
              <Icon size={13} />
              {item.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
