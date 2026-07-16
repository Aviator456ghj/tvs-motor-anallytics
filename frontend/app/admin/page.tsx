"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

interface DashboardSummary {
  total_businesses: number;
  pending_approvals: number;
  total_customers: number;
  total_bookings: number;
  completed_bookings: number;
  gross_revenue: number;
  commission_revenue: number;
  open_support_tickets: number;
  bookings_last_30_days: number;
}

export default function AdminOverview() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    api.get<DashboardSummary>("/admin/dashboard").then(setData);
  }, []);

  if (!data) return <Spinner />;

  return (
    <div>
      <PageHeader title="Platform overview" description="Marketplace health at a glance." />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard label="Total businesses" value={data.total_businesses} sub={`${data.pending_approvals} pending approval`} />
        <StatCard label="Total customers" value={data.total_customers} />
        <StatCard label="Total bookings" value={data.total_bookings} sub={`${data.bookings_last_30_days} in last 30 days`} />
        <StatCard label="Completed bookings" value={data.completed_bookings} />
        <StatCard label="Gross revenue" value={`₹${data.gross_revenue.toLocaleString()}`} />
        <StatCard label="Commission revenue" value={`₹${data.commission_revenue.toLocaleString()}`} />
        <StatCard label="Open support tickets" value={data.open_support_tickets} />
      </div>
    </div>
  );
}
