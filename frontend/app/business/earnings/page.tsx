"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

interface Analytics {
  gross_earnings: number;
  commission_paid: number;
  net_earnings: number;
  completed_bookings: number;
}

export default function EarningsPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  useEffect(() => {
    api.get<Analytics>("/analytics/business/me").then(setAnalytics);
  }, []);

  if (!analytics) return <Spinner />;

  return (
    <div>
      <PageHeader title="Earnings" description="Gross revenue, platform commission, and your net payout." />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Gross earnings" value={`₹${analytics.gross_earnings.toLocaleString()}`} />
        <StatCard label="Commission paid" value={`₹${analytics.commission_paid.toLocaleString()}`} />
        <StatCard label="Net earnings" value={`₹${analytics.net_earnings.toLocaleString()}`} />
        <StatCard label="Completed bookings" value={analytics.completed_bookings} />
      </div>
    </div>
  );
}
