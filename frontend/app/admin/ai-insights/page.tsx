"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

interface FraudSignal {
  business_id: string;
  cancellation_rate: number;
  risk_level: "low" | "medium" | "high";
}

const RISK_STYLES: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
};

export default function AiInsightsPage() {
  const [rows, setRows] = useState<{ business: Business; signal: FraudSignal }[] | null>(null);

  useEffect(() => {
    api.get<Business[]>("/admin/businesses").then(async (businesses) => {
      const results = await Promise.all(
        businesses.map(async (business) => ({
          business,
          signal: await api.get<FraudSignal>(`/ai/fraud-signals/business/${business.id}`),
        }))
      );
      setRows(results);
    });
  }, []);

  if (!rows) return <Spinner />;

  return (
    <div>
      <PageHeader title="AI Insights" description="Fraud risk signals derived from booking cancellation patterns." />
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Business</th>
              <th className="px-4 py-3">Cancellation rate</th>
              <th className="px-4 py-3">Risk level</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map(({ business, signal }) => (
              <tr key={business.id}>
                <td className="px-4 py-3 font-medium text-slate-800">{business.company_name}</td>
                <td className="px-4 py-3 text-slate-500">{(signal.cancellation_rate * 100).toFixed(0)}%</td>
                <td className="px-4 py-3">
                  <span className={`badge ${RISK_STYLES[signal.risk_level]}`}>{signal.risk_level}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-xs text-slate-400">
        Heuristic signal today (cancellation-rate threshold). See docs/ROADMAP.md for the planned anomaly-detection
        model.
      </p>
    </div>
  );
}
