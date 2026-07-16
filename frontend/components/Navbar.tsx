"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Navbar() {
  const { user, logout } = useAuth();

  const dashboardHref = user?.role === "admin" ? "/admin" : user?.role === "business" ? "/business" : "/dashboard";

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="text-lg font-bold text-brand-700">
          Services<span className="text-slate-900">OS</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex">
          <Link href="/browse" className="hover:text-brand-700">
            Browse Services
          </Link>
          <Link href="/search" className="hover:text-brand-700">
            Search
          </Link>
          {user?.role === "business" ? (
            <span className="text-slate-400">Business Portal</span>
          ) : (
            <Link href="/business/onboarding" className="hover:text-brand-700">
              List Your Business
            </Link>
          )}
        </nav>
        <div className="flex items-center gap-3">
          {user ? (
            <>
              <Link href={dashboardHref} className="btn-secondary">
                Dashboard
              </Link>
              <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-800">
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-brand-700">
                Log in
              </Link>
              <Link href="/register" className="btn-primary">
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
