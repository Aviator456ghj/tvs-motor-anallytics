"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

interface Analytics {
  total_bookings: number;
  bookings_last_n_days: number;
  completed_bookings: number;
  cancelled_bookings: number;
  conversion_rate: number;
  rating_avg: number;
  rating_count: number;
  status_breakdown: Record<string, number>;
}

export default function BusinessAnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);

  useEffect(() => {
    api.get<Analytics>("/analytics/business/me").then(setData);
  }, []);

  if (!data) return <Spinner />;

  return (
    <div>
      <PageHeader title="Analytics" description="Performance over the last 30 days." />
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Bookings (30d)" value={data.bookings_last_n_days} />
        <StatCard label="Conversion rate" value={`${(data.conversion_rate * 100).toFixed(0)}%`} />
        <StatCard label="Cancelled" value={data.cancelled_bookings} />
        <StatCard label="Rating" value={`${data.rating_avg.toFixed(1)} ★`} sub={`${data.rating_count} reviews`} />
      </div>
      <div className="card">
        <h3 className="mb-3 font-semibold text-slate-900">Status breakdown</h3>
        <div className="space-y-2">
          {Object.entries(data.status_breakdown).map(([status, count]) => (
            <div key={status} className="flex items-center gap-3">
              <span className="w-28 shrink-0 text-sm capitalize text-slate-600">{status.replace("_", " ")}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-brand-600"
                  style={{ width: `${(count / data.total_bookings) * 100}%` }}
                />
              </div>
              <span className="w-8 text-right text-sm text-slate-500">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
