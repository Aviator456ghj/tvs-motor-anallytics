"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

export default function ReportsPage() {
  const [businesses, setBusinesses] = useState<Business[] | null>(null);

  useEffect(() => {
    api.get<Business[]>("/admin/businesses").then(setBusinesses);
  }, []);

  if (!businesses) return <Spinner />;

  const byCity = businesses.reduce<Record<string, number>>((acc, b) => {
    const key = b.city || "Unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const topRated = [...businesses].sort((a, b) => b.rating_avg - a.rating_avg).slice(0, 5);

  return (
    <div>
      <PageHeader title="Reports" description="Operational reports derived from live marketplace data." />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-3 font-semibold text-slate-900">Businesses by city</h3>
          <div className="space-y-2">
            {Object.entries(byCity).map(([city, count]) => (
              <div key={city} className="flex items-center gap-3 text-sm">
                <span className="w-32 shrink-0 text-slate-600">{city}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand-600" style={{ width: `${(count / businesses.length) * 100}%` }} />
                </div>
                <span className="w-6 text-right text-slate-500">{count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h3 className="mb-3 font-semibold text-slate-900">Top rated providers</h3>
          <div className="space-y-2 text-sm">
            {topRated.map((b) => (
              <div key={b.id} className="flex items-center justify-between">
                <span className="text-slate-700">{b.company_name}</span>
                <span className="text-amber-600">★ {b.rating_avg.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
