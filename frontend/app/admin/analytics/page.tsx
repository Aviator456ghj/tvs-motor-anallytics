"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

interface DemandForecast {
  trailing_30_day_bookings: number;
  forecast_next_30_days: number;
}

export default function AdminAnalyticsPage() {
  const [forecast, setForecast] = useState<DemandForecast | null>(null);

  useEffect(() => {
    api.get<DemandForecast>("/ai/demand-forecast").then(setForecast);
  }, []);

  if (!forecast) return <Spinner />;

  return (
    <div>
      <PageHeader title="Analytics" description="Platform-wide demand trends, powered by the AI Service." />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard label="Bookings, trailing 30 days" value={forecast.trailing_30_day_bookings} />
        <StatCard label="Forecast, next 30 days" value={forecast.forecast_next_30_days} sub="Naive baseline — swap for a real time-series model" />
      </div>
    </div>
  );
}
