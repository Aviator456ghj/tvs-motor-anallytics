"use client";

import { useState } from "react";
import {
  Search,
  Sparkles,
  Share2,
  MessageSquare,
  Bell,
  HelpCircle,
  ChevronDown,
  Store,
  Check,
  LayoutGrid,
  LayoutDashboard,
  Monitor,
  Users,
  BarChart2,
  ShoppingBag,
  CreditCard,
  RotateCcw,
  ShieldAlert,
  Boxes,
  Truck,
  Puzzle,
  AtSign,
  CheckCheck,
  type LucideIcon,
} from "lucide-react";
import {
  storeSwitcherItems,
  appSwitcherItems,
  notifications as notificationsSeed,
  type NotificationType,
} from "@/lib/dashboard-data";

const appIconMap: Record<string, LucideIcon> = {
  "layout-dashboard": LayoutDashboard,
  monitor: Monitor,
  store: Store,
  users: Users,
  sparkles: Sparkles,
  "bar-chart-2": BarChart2,
};

const notificationIconMap: Record<NotificationType, { icon: LucideIcon; color: string; bg: string }> = {
  order: { icon: ShoppingBag, color: "text-blue-500", bg: "bg-blue-50" },
  "payment-failed": { icon: CreditCard, color: "text-red-500", bg: "bg-red-50" },
  refund: { icon: RotateCcw, color: "text-orange-500", bg: "bg-orange-50" },
  chargeback: { icon: ShieldAlert, color: "text-rose-500", bg: "bg-rose-50" },
  inventory: { icon: Boxes, color: "text-amber-500", bg: "bg-amber-50" },
  shipping: { icon: Truck, color: "text-cyan-500", bg: "bg-cyan-50" },
  app: { icon: Puzzle, color: "text-violet-500", bg: "bg-violet-50" },
  mention: { icon: AtSign, color: "text-indigo-500", bg: "bg-indigo-50" },
};

export default function Topbar() {
  const [storeMenuOpen, setStoreMenuOpen] = useState(false);
  const [appMenuOpen, setAppMenuOpen] = useState(false);
  const [notifMenuOpen, setNotifMenuOpen] = useState(false);
  const [activeStore, setActiveStore] = useState(storeSwitcherItems[0].id);
  const [notifications, setNotifications] = useState(notificationsSeed);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <header className="sticky top-0 z-20 h-16 shrink-0 flex items-center justify-between gap-3 px-6 bg-card-bg border-b border-card-border">
      <div className="flex items-center gap-3 min-w-0">
        {/* Store selector */}
        <div className="relative shrink-0 hidden md:block">
          <button
            onClick={() => setStoreMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg border border-card-border px-2.5 py-2 hover:bg-background/80 transition-colors"
          >
            <span className="w-6 h-6 rounded-md bg-gradient-to-br from-brand-start to-brand-end flex items-center justify-center shrink-0">
              <Store size={13} className="text-white" />
            </span>
            <span className="text-[12.5px] font-medium text-foreground max-w-[110px] truncate hidden lg:block">
              {storeSwitcherItems.find((s) => s.id === activeStore)?.name}
            </span>
            <ChevronDown size={13} className="text-muted-light" />
          </button>
          {storeMenuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setStoreMenuOpen(false)} />
              <div className="absolute left-0 top-full mt-1 w-64 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                <div className="px-3 py-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-muted-light">
                  Switch store
                </div>
                {storeSwitcherItems.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      setActiveStore(s.id);
                      setStoreMenuOpen(false);
                    }}
                    className="w-full flex items-center justify-between gap-2 px-3 py-2 hover:bg-background/80"
                  >
                    <span className="text-left">
                      <div className="text-[12.5px] font-medium text-foreground">{s.name}</div>
                      <div className="text-[11px] text-muted-light">{s.domain}</div>
                    </span>
                    {s.id === activeStore && <Check size={14} className="text-brand-start shrink-0" />}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="relative w-full max-w-[300px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-light" size={16} />
          <input
            type="text"
            placeholder="Search anything..."
            className="w-full pl-9 pr-14 py-2 rounded-lg border border-card-border bg-background/60 text-sm placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30 focus:border-brand-start/50"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-medium text-muted-light border border-card-border rounded px-1.5 py-0.5">
            ⌘K
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white text-[13px] font-medium px-4 py-2 shadow-sm hover:opacity-90 transition-opacity">
          <Sparkles size={15} />
          <span className="hidden sm:inline">Ask AI Assistant</span>
        </button>

        {/* App switcher */}
        <div className="relative">
          <IconButton icon={LayoutGrid} onClick={() => setAppMenuOpen((v) => !v)} />
          {appMenuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setAppMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-60 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 p-2 grid grid-cols-3 gap-1">
                {appSwitcherItems.map((app) => {
                  const AppIcon = appIconMap[app.icon] ?? LayoutGrid;
                  return (
                    <button
                      key={app.id}
                      onClick={() => setAppMenuOpen(false)}
                      className="flex flex-col items-center gap-1.5 rounded-lg py-2.5 hover:bg-background/80"
                    >
                      <span className="w-8 h-8 rounded-lg bg-background flex items-center justify-center text-brand-start">
                        <AppIcon size={15} />
                      </span>
                      <span className="text-[10.5px] font-medium text-foreground text-center leading-tight">{app.label}</span>
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>

        <IconButton icon={Share2} />
        <IconButton icon={MessageSquare} badge={8} badgeColor="bg-red-500" />

        {/* Notifications */}
        <div className="relative">
          <IconButton icon={Bell} badge={unreadCount || undefined} badgeColor="bg-red-500" onClick={() => setNotifMenuOpen((v) => !v)} />
          {notifMenuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setNotifMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-80 bg-card-bg border border-card-border rounded-lg shadow-lg z-20">
                <div className="flex items-center justify-between px-4 py-3 border-b border-card-border">
                  <span className="text-[13px] font-semibold text-foreground">Notifications</span>
                  <button
                    onClick={() => setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))}
                    className="flex items-center gap-1 text-[11.5px] font-medium text-brand-start hover:underline"
                  >
                    <CheckCheck size={13} /> Mark all read
                  </button>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notifications.map((n) => {
                    const meta = notificationIconMap[n.type];
                    const NotifIcon = meta.icon;
                    return (
                      <button
                        key={n.id}
                        onClick={() =>
                          setNotifications((prev) => prev.map((x) => (x.id === n.id ? { ...x, read: true } : x)))
                        }
                        className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-background/80 border-b border-card-border/60 last:border-b-0 ${
                          n.read ? "" : "bg-brand-start/[0.04]"
                        }`}
                      >
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${meta.bg} ${meta.color}`}>
                          <NotifIcon size={14} />
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className="flex items-center gap-1.5">
                            <span className="text-[12.5px] font-semibold text-foreground truncate">{n.title}</span>
                            {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-brand-start shrink-0" />}
                          </span>
                          <div className="text-[11.5px] text-muted truncate">{n.body}</div>
                          <div className="text-[10.5px] text-muted-light mt-0.5">{n.time}</div>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>

        <IconButton icon={HelpCircle} />

        <button className="flex items-center gap-2.5 pl-2 pr-1 py-1 rounded-lg hover:bg-background/80 transition-colors">
          <span className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-start to-brand-end flex items-center justify-center text-white text-[12px] font-semibold shrink-0">
            JD
          </span>
          <div className="text-left leading-tight hidden sm:block">
            <div className="text-[13px] font-semibold text-foreground">John Doe</div>
            <div className="text-[11px] text-muted-light">Owner</div>
          </div>
          <ChevronDown size={14} className="text-muted-light hidden sm:block" />
        </button>
      </div>
    </header>
  );
}

function IconButton({
  icon: Icon,
  badge,
  badgeColor = "bg-red-500",
  onClick,
}: {
  icon: LucideIcon;
  badge?: number;
  badgeColor?: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="relative w-9 h-9 flex items-center justify-center rounded-lg text-muted hover:bg-background/80 transition-colors"
    >
      <Icon size={17} />
      {badge !== undefined && (
        <span
          className={`absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full ${badgeColor} text-white text-[10px] font-semibold flex items-center justify-center`}
        >
          {badge}
        </span>
      )}
    </button>
  );
}
