"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Payout } from "@/lib/types";

export default function AdminPayoutsPage() {
  const [payouts, setPayouts] = useState<Payout[] | null>(null);

  useEffect(() => {
    api.get<Payout[]>("/admin/payouts").then(setPayouts);
  }, []);

  if (!payouts) return <Spinner />;

  const total = payouts.reduce((sum, p) => sum + p.amount, 0);

  return (
    <div>
      <PageHeader title="Payouts" description="Every payout issued to businesses across the platform." />
      <div className="mb-6 max-w-xs">
        <div className="card">
          <p className="text-sm text-slate-500">Total paid out</p>
          <p className="text-xl font-bold text-slate-900">₹{total.toLocaleString()}</p>
        </div>
      </div>
      {payouts.length === 0 ? (
        <EmptyState message="No payouts issued yet." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {payouts.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{p.reference}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">₹{p.amount.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className="badge bg-emerald-100 text-emerald-700">{p.status}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
