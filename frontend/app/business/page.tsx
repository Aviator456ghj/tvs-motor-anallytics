"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import TrendChart, { TrendPoint } from "@/components/TrendChart";
import { api, ApiError } from "@/lib/api";
import { Business, BookingListItem } from "@/lib/types";

interface Analytics {
  total_bookings: number;
  completed_bookings: number;
  gross_earnings: number;
  net_earnings: number;
  rating_avg: number;
  rating_count: number;
}
interface DayPoint {
  date: string;
  bookings: number;
  revenue: number;
}
interface PayoutBalance {
  available_balance: number;
}

export default function BusinessOverview() {
  const router = useRouter();
  const [business, setBusiness] = useState<Business | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [series, setSeries] = useState<DayPoint[] | null>(null);
  const [pendingOrders, setPendingOrders] = useState<BookingListItem[] | null>(null);
  const [hasPayoutAccount, setHasPayoutAccount] = useState<boolean | null>(null);
  const [notFoundYet, setNotFoundYet] = useState(false);

  useEffect(() => {
    api
      .get<Business>("/businesses/me")
      .then((b) => {
        setBusiness(b);
        api.get<Analytics>("/analytics/business/me").then(setAnalytics);
        api.get<DayPoint[]>("/analytics/business/me/timeseries?days=14").then(setSeries);
        api.get<BookingListItem[]>("/bookings?status_filter=requested").then(setPendingOrders);
        api
          .get("/businesses/me/payout-account")
          .then((a) => setHasPayoutAccount(!!a))
          .catch(() => setHasPayoutAccount(false));
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setNotFoundYet(true);
      });
  }, []);

  if (notFoundYet) {
    return (
      <div className="card text-center">
        <h2 className="mb-2 font-semibold text-slate-900">Finish setting up your business</h2>
        <p className="mb-4 text-sm text-slate-500">Create your business profile to start receiving bookings.</p>
        <button className="btn-primary" onClick={() => router.push("/business/onboarding")}>
          Set up business profile
        </button>
      </div>
    );
  }

  if (!business || !analytics) return <Spinner />;

  const todos: { text: string; href: string }[] = [];
  if (!business.is_approved) todos.push({ text: "Submit KYC documents to get approved", href: "/business/documents" });
  if (pendingOrders && pendingOrders.length > 0) todos.push({ text: `Respond to ${pendingOrders.length} pending order${pendingOrders.length === 1 ? "" : "s"}`, href: "/business/bookings" });
  if (hasPayoutAccount === false) todos.push({ text: "Add a payout bank account", href: "/business/settings/payout-account" });

  const points: TrendPoint[] = (series || []).map((d) => ({ date: d.date, value: d.revenue }));

  return (
    <div>
      <PageHeader
        title={business.company_name}
        description={business.is_approved ? "Your business is live and visible to customers." : "Your profile is pending admin approval."}
      />

      {todos.length > 0 && (
        <div className="card mb-6">
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Things to do</h3>
          <div className="space-y-1.5">
            {todos.map((t) => (
              <Link key={t.href} href={t.href} className="flex items-center justify-between rounded-lg px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
                <span>{t.text}</span>
                <span className="text-brand-600">→</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total bookings" value={analytics.total_bookings} />
        <StatCard label="Completed" value={analytics.completed_bookings} />
        <StatCard label="Gross earnings" value={`₹${analytics.gross_earnings.toLocaleString()}`} />
        <StatCard label="Rating" value={`${analytics.rating_avg.toFixed(1)} ★`} sub={`${analytics.rating_count} reviews`} />
      </div>

      <div className="card">
        <h3 className="mb-3 font-semibold text-slate-900">Revenue — last 14 days</h3>
        {series ? <TrendChart data={points} valueFormatter={(v) => `₹${v.toLocaleString()}`} /> : <Spinner />}
      </div>
    </div>
  );
}
