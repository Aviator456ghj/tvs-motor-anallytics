"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { ReactNode, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import NotificationBell from "@/components/NotificationBell";
import {
  HomeIcon,
  OrdersIcon,
  ProductsIcon,
  CustomersIcon,
  DiscountIcon,
  FinanceIcon,
  AnalyticsIcon,
  StoreIcon,
  SettingsIcon,
  SearchIcon,
  PlusIcon,
  ChevronDownIcon,
} from "@/components/icons";

interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: (p: { className?: string }) => JSX.Element;
  children?: { href: string; label: string }[];
}

const NAV: NavItem[] = [
  { id: "home", label: "Home", href: "/business", icon: HomeIcon },
  { id: "orders", label: "Orders", href: "/business/bookings", icon: OrdersIcon },
  {
    id: "products",
    label: "Products",
    href: "/business/services",
    icon: ProductsIcon,
    children: [
      { href: "/business/services", label: "Services & packages" },
      { href: "/business/pricing", label: "Pricing" },
    ],
  },
  {
    id: "customers",
    label: "Customers",
    href: "/business/customers",
    icon: CustomersIcon,
    children: [
      { href: "/business/customers", label: "All customers" },
      { href: "/business/reviews", label: "Reviews" },
    ],
  },
  { id: "discounts", label: "Discounts", href: "/business/discounts", icon: DiscountIcon },
  {
    id: "finance",
    label: "Finance",
    href: "/business/payouts",
    icon: FinanceIcon,
    children: [
      { href: "/business/payouts", label: "Payouts" },
      { href: "/business/finance", label: "Transactions" },
      { href: "/business/earnings", label: "Earnings" },
    ],
  },
  {
    id: "analytics",
    label: "Analytics",
    href: "/business/analytics",
    icon: AnalyticsIcon,
    children: [
      { href: "/business/analytics", label: "Overview" },
      { href: "/business/reports", label: "Reports" },
    ],
  },
  {
    id: "store",
    label: "Online Store",
    href: "/business/profile",
    icon: StoreIcon,
    children: [
      { href: "/business/profile", label: "Company profile" },
      { href: "/business/portfolio", label: "Portfolio" },
      { href: "/business/calendar", label: "Calendar" },
      { href: "/business/availability", label: "Availability" },
    ],
  },
  { id: "settings", label: "Settings", href: "/business/settings", icon: SettingsIcon },
];

function CreateMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const options = [
    { label: "Create order", href: "/business/bookings?create=1" },
    { label: "Add service", href: "/business/services?create=1" },
    { label: "Add discount", href: "/business/discounts?create=1" },
  ];

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((v) => !v)} className="btn-primary flex items-center gap-1.5 text-sm">
        <PlusIcon className="h-4 w-4" />
        Create
        <ChevronDownIcon className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-52 rounded-xl border border-slate-200 bg-white py-1.5 shadow-lg">
          {options.map((o) => (
            <button
              key={o.href}
              onClick={() => {
                setOpen(false);
                router.push(o.href);
              }}
              className="block w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function BusinessShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const router = useRouter();
  const [search, setSearch] = useState("");

  const activeSection = NAV.find((n) => pathname === n.href || n.children?.some((c) => pathname === c.href)) || NAV[0];

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex">
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
          <div className="border-b border-slate-200 px-4 py-3.5">
            <Link href="/" className="text-base font-bold text-brand-700">
              Services<span className="text-slate-900">OS</span>
            </Link>
            <p className="mt-0.5 truncate text-xs font-medium text-slate-400">Business admin</p>
          </div>
          <nav className="flex-1 space-y-0.5 overflow-y-auto px-2.5 py-3">
            {NAV.map((item) => {
              const isActive = activeSection.id === item.id;
              const Icon = item.icon;
              return (
                <div key={item.id}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13.5px] font-medium transition ${
                      isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    <Icon className={isActive ? "text-brand-600" : "text-slate-400"} />
                    {item.label}
                  </Link>
                  {isActive && item.children && (
                    <div className="ml-[26px] mt-0.5 space-y-0.5 border-l border-slate-200 pl-3">
                      {item.children.map((c) => (
                        <Link
                          key={c.href}
                          href={c.href}
                          className={`block rounded-md px-2 py-1.5 text-[13px] ${
                            pathname === c.href ? "font-semibold text-brand-700" : "text-slate-500 hover:text-slate-800"
                          }`}
                        >
                          {c.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </nav>
          <div className="border-t border-slate-200 p-3.5">
            <p className="truncate text-[13px] font-medium text-slate-800">{user?.full_name}</p>
            <p className="truncate text-[11.5px] text-slate-500">{user?.email}</p>
            <button onClick={logout} className="mt-1.5 text-[11.5px] font-medium text-red-600 hover:underline">
              Sign out
            </button>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-2.5 backdrop-blur sm:px-6">
            <form
              className="relative hidden max-w-xs flex-1 sm:block"
              onSubmit={(e) => {
                e.preventDefault();
                router.push(`/business/bookings?q=${encodeURIComponent(search)}`);
              }}
            >
              <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search orders, customers…"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-8 pr-3 text-[13px] focus:border-brand-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </form>
            <div className="ml-auto flex items-center gap-2">
              <NotificationBell />
              <CreateMenu />
            </div>
          </header>
          <main className="p-4 sm:p-6 lg:p-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
