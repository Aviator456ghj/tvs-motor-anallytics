"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { useAuth } from "@/lib/auth";

export interface NavSection {
  label: string;
  items: { href: string; label: string }[];
}

export default function DashboardShell({
  title,
  sections,
  children,
}: {
  title: string;
  sections: NavSection[];
  children: ReactNode;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
          <div className="border-b border-slate-200 px-5 py-4">
            <Link href="/" className="text-lg font-bold text-brand-700">
              Services<span className="text-slate-900">OS</span>
            </Link>
            <p className="mt-0.5 text-xs font-medium uppercase tracking-wide text-slate-400">{title}</p>
          </div>
          <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
            {sections.map((section) => (
              <div key={section.label}>
                <p className="px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{section.label}</p>
                <div className="mt-1 space-y-0.5">
                  {section.items.map((item) => {
                    const active = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`block rounded-lg px-2.5 py-1.5 text-sm font-medium transition ${
                          active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                        }`}
                      >
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>
          <div className="border-t border-slate-200 p-4">
            <p className="truncate text-sm font-medium text-slate-800">{user?.full_name}</p>
            <p className="truncate text-xs text-slate-500">{user?.email}</p>
            <button onClick={logout} className="mt-2 text-xs font-medium text-red-600 hover:underline">
              Sign out
            </button>
          </div>
        </aside>
        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
