"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

interface DashboardSummary {
  total_bookings: number;
  completed_bookings: number;
  gross_revenue: number;
  commission_revenue: number;
  bookings_last_30_days: number;
}

export default function RevenuePage() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    api.get<DashboardSummary>("/admin/dashboard").then(setData);
  }, []);

  if (!data) return <Spinner />;

  const avgOrderValue = data.completed_bookings ? data.gross_revenue / data.completed_bookings : 0;

  return (
    <div>
      <PageHeader title="Revenue" description="Platform-wide gross revenue and commission earnings." />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Gross revenue" value={`₹${data.gross_revenue.toLocaleString()}`} />
        <StatCard label="Commission revenue" value={`₹${data.commission_revenue.toLocaleString()}`} sub="Platform's share" />
        <StatCard label="Avg. order value" value={`₹${avgOrderValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
        <StatCard label="Bookings (30d)" value={data.bookings_last_30_days} />
      </div>
    </div>
  );
}
