"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import TrendChart, { TrendPoint } from "@/components/TrendChart";
import { api } from "@/lib/api";

interface DemandForecast {
  trailing_30_day_bookings: number;
  forecast_next_30_days: number;
}

interface DayPoint {
  date: string;
  bookings: number;
  revenue: number;
}

export default function AdminAnalyticsPage() {
  const [forecast, setForecast] = useState<DemandForecast | null>(null);
  const [series, setSeries] = useState<DayPoint[] | null>(null);
  const [metric, setMetric] = useState<"revenue" | "bookings">("revenue");

  useEffect(() => {
    api.get<DemandForecast>("/ai/demand-forecast").then(setForecast);
    api.get<DayPoint[]>("/admin/dashboard/timeseries?days=30").then(setSeries);
  }, []);

  if (!forecast || !series) return <Spinner />;

  const points: TrendPoint[] = series.map((d) => ({ date: d.date, value: metric === "revenue" ? d.revenue : d.bookings }));

  return (
    <div>
      <PageHeader title="Analytics" description="Platform-wide demand trends." />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard label="Bookings, trailing 30 days" value={forecast.trailing_30_day_bookings} />
        <StatCard label="Forecast, next 30 days" value={forecast.forecast_next_30_days} sub="Naive baseline — swap for a real time-series model" />
      </div>

      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Platform {metric === "revenue" ? "revenue" : "bookings"} — last 30 days</h3>
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
    </div>
  );
}
