"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import TrendChart, { TrendPoint } from "@/components/TrendChart";
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

interface DayPoint {
  date: string;
  bookings: number;
  revenue: number;
}

export default function BusinessAnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [series, setSeries] = useState<DayPoint[] | null>(null);
  const [metric, setMetric] = useState<"revenue" | "bookings">("revenue");

  useEffect(() => {
    api.get<Analytics>("/analytics/business/me").then(setData);
    api.get<DayPoint[]>("/analytics/business/me/timeseries?days=30").then(setSeries);
  }, []);

  if (!data || !series) return <Spinner />;

  const points: TrendPoint[] = series.map((d) => ({ date: d.date, value: metric === "revenue" ? d.revenue : d.bookings }));

  return (
    <div>
      <PageHeader title="Analytics" description="Performance over the last 30 days." />
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Bookings (30d)" value={data.bookings_last_n_days} />
        <StatCard label="Conversion rate" value={`${(data.conversion_rate * 100).toFixed(0)}%`} />
        <StatCard label="Cancelled" value={data.cancelled_bookings} />
        <StatCard label="Rating" value={`${data.rating_avg.toFixed(1)} ★`} sub={`${data.rating_count} reviews`} />
      </div>

      <div className="card mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">{metric === "revenue" ? "Revenue" : "Bookings"} — last 30 days</h3>
          <div className="flex gap-1">
            <button
              onClick={() => setMetric("revenue")}
              className={`badge ${metric === "revenue" ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-500"}`}
            >
              Revenue
            </button>
            <button
              onClick={() => setMetric("bookings")}
              className={`badge ${metric === "bookings" ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-500"}`}
            >
              Bookings
            </button>
          </div>
        </div>
        <TrendChart data={points} valueFormatter={(v) => (metric === "revenue" ? `₹${v.toLocaleString()}` : `${v} bookings`)} />
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
