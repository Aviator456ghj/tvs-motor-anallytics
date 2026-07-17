"use client";

import { useState } from "react";
import {
  LayoutDashboard,
  ShoppingBag,
  Package,
  Users,
  Megaphone,
  Percent,
  FileText,
  Globe,
  BarChart2,
  Wallet,
  Grid3x3,
  Zap,
  Sparkles,
  Monitor,
  Store,
  Smartphone,
  MousePointerClick,
  Settings,
  ChevronsLeft,
  ChevronsRight,
  Eye,
  Plus,
  ShieldCheck,
  Building2,
  type LucideIcon,
} from "lucide-react";
import clsx from "clsx";
import { mainNav, salesChannels } from "@/lib/dashboard-data";

const iconMap: Record<string, LucideIcon> = {
  "layout-dashboard": LayoutDashboard,
  "shopping-bag": ShoppingBag,
  package: Package,
  users: Users,
  megaphone: Megaphone,
  percent: Percent,
  "file-text": FileText,
  globe: Globe,
  "bar-chart-2": BarChart2,
  wallet: Wallet,
  grid: Grid3x3,
  zap: Zap,
  sparkles: Sparkles,
  monitor: Monitor,
  store: Store,
  smartphone: Smartphone,
  "mouse-pointer-click": MousePointerClick,
};

const channelBadge: Record<string, { label: string; className: string }> = {
  facebook: { label: "f", className: "bg-[#1877F2] text-white" },
  amazon: { label: "a", className: "bg-[#FF9900] text-white" },
  tiktok: { label: "t", className: "bg-black text-white" },
};

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={clsx(
        "hidden lg:flex flex-col shrink-0 bg-sidebar-bg text-sidebar-text h-screen sticky top-0 transition-all duration-200",
        collapsed ? "w-[76px]" : "w-[248px]"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-16 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-start to-brand-end flex items-center justify-center shrink-0">
          <ShieldCheck className="w-4.5 h-4.5 text-white" size={18} />
        </div>
        {!collapsed && (
          <div className="leading-tight overflow-hidden">
            <div className="text-white font-semibold text-[15px] tracking-tight">CommerceOS</div>
            <div className="text-[10px] text-sidebar-text/70 whitespace-nowrap">AI-First Commerce Platform</div>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4 space-y-0.5">
        {mainNav.map((item) => {
          const Icon = iconMap[item.icon] ?? LayoutDashboard;
          const active = item.id === "dashboard";
          return (
            <a
              key={item.id}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13.5px] font-medium transition-colors group relative",
                active
                  ? "bg-sidebar-bg-active text-sidebar-text-active"
                  : "text-sidebar-text hover:bg-sidebar-bg-hover hover:text-white"
              )}
            >
              <Icon size={17} className="shrink-0" strokeWidth={2} />
              {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
              {!collapsed && item.badge && (
                <span
                  className={clsx(
                    "text-[10px] font-semibold px-1.5 py-0.5 rounded-full shrink-0",
                    item.badge === "New"
                      ? "bg-gradient-to-r from-brand-start to-brand-end text-white"
                      : active
                        ? "bg-white/20 text-white"
                        : "bg-white/10 text-sidebar-text"
                  )}
                >
                  {item.badge}
                </span>
              )}
            </a>
          );
        })}

        {/* Sales channels */}
        <div className="pt-5">
          {!collapsed && (
            <div className="px-3 pb-2 text-[10.5px] font-semibold uppercase tracking-wider text-sidebar-text/50 flex items-center gap-1.5">
              <Building2 size={11} /> Sales Channels
            </div>
          )}
          {salesChannels.map((c) => {
            const badge = channelBadge[c.id];
            const Icon = iconMap[c.icon];
            return (
              <a
                key={c.id}
                href="#"
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-[13.5px] text-sidebar-text hover:bg-sidebar-bg-hover hover:text-white transition-colors group"
              >
                {badge ? (
                  <span className={clsx("w-[17px] h-[17px] rounded-[4px] flex items-center justify-center text-[10px] font-bold shrink-0", badge.className)}>
                    {badge.label}
                  </span>
                ) : Icon ? (
                  <Icon size={17} className="shrink-0" strokeWidth={2} />
                ) : null}
                {!collapsed && <span className="flex-1 truncate">{c.label}</span>}
                {!collapsed && c.eye && (
                  <Eye size={14} className="text-sidebar-text/40 shrink-0" />
                )}
              </a>
            );
          })}
          {!collapsed && (
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-[13.5px] text-sidebar-text/70 hover:bg-sidebar-bg-hover hover:text-white transition-colors"
            >
              <Plus size={17} strokeWidth={2} />
              <span>Add channel</span>
            </a>
          )}
        </div>
      </nav>

      <div className="border-t border-white/5 px-3 py-3 space-y-0.5">
        <a
          href="#"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13.5px] font-medium text-sidebar-text hover:bg-sidebar-bg-hover hover:text-white transition-colors"
        >
          <Settings size={17} strokeWidth={2} />
          {!collapsed && <span>Settings</span>}
        </a>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13.5px] font-medium text-sidebar-text hover:bg-sidebar-bg-hover hover:text-white transition-colors"
        >
          {collapsed ? <ChevronsRight size={17} /> : <ChevronsLeft size={17} />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
