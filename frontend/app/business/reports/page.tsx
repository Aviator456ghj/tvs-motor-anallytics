"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface TopService {
  service: string;
  bookings: number;
  revenue: number;
}
interface RepeatCustomers {
  total_customers: number;
  repeat_customers: number;
  repeat_rate: number;
}
interface FunnelStage {
  stage: string;
  count: number;
}

export default function ReportsPage() {
  const [topServices, setTopServices] = useState<TopService[] | null>(null);
  const [repeat, setRepeat] = useState<RepeatCustomers | null>(null);
  const [funnel, setFunnel] = useState<FunnelStage[] | null>(null);

  useEffect(() => {
    api.get<TopService[]>("/analytics/business/me/reports/top-services").then(setTopServices);
    api.get<RepeatCustomers>("/analytics/business/me/reports/repeat-customers").then(setRepeat);
    api.get<FunnelStage[]>("/analytics/business/me/reports/funnel").then(setFunnel);
  }, []);

  if (!topServices || !repeat || !funnel) return <Spinner />;

  const maxRevenue = Math.max(1, ...topServices.map((s) => s.revenue));
  const maxFunnel = Math.max(1, ...funnel.map((f) => f.count));

  return (
    <div>
      <PageHeader title="Reports" description="Deeper cuts of your performance data." />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total customers" value={repeat.total_customers} />
        <StatCard label="Repeat customers" value={repeat.repeat_customers} />
        <StatCard label="Repeat rate" value={`${(repeat.repeat_rate * 100).toFixed(0)}%`} sub="Customers with 2+ orders" />
      </div>

      <div className="card mb-6">
        <h3 className="mb-4 font-semibold text-slate-900">Sales by service</h3>
        {topServices.length === 0 ? (
          <EmptyState message="No sales yet." />
        ) : (
          <div className="space-y-3">
            {topServices.map((s) => (
              <div key={s.service} className="flex items-center gap-3">
                <span className="w-40 shrink-0 truncate text-sm text-slate-600">{s.service}</span>
                <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand-600" style={{ width: `${(s.revenue / maxRevenue) * 100}%` }} />
                </div>
                <span className="w-24 shrink-0 text-right text-sm font-medium text-slate-800">₹{s.revenue.toLocaleString()}</span>
                <span className="w-16 shrink-0 text-right text-xs text-slate-400">{s.bookings} orders</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="mb-4 font-semibold text-slate-900">Booking funnel</h3>
        <div className="space-y-3">
          {funnel.map((f, i) => (
            <div key={f.stage} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-sm text-slate-600">{f.stage}</span>
              <div className="h-6 flex-1 overflow-hidden rounded-md bg-slate-100">
                <div
                  className="flex h-full items-center rounded-md bg-brand-600 px-2 text-xs font-medium text-white"
                  style={{ width: `${Math.max((f.count / maxFunnel) * 100, f.count > 0 ? 8 : 0)}%` }}
                >
                  {f.count}
                </div>
              </div>
              {i > 0 && funnel[i - 1].count > 0 && (
                <span className="w-14 shrink-0 text-right text-xs text-slate-400">{Math.round((f.count / funnel[i - 1].count) * 100)}%</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
