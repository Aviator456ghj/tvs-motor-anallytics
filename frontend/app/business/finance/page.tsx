"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface Transaction {
  date: string;
  type: "payment" | "refund" | "payout";
  description: string;
  amount: number;
  running_balance: number;
}

const TYPE_STYLES: Record<string, string> = {
  payment: "bg-emerald-100 text-emerald-700",
  refund: "bg-red-100 text-red-700",
  payout: "bg-slate-200 text-slate-600",
};

export default function FinancePage() {
  const [rows, setRows] = useState<Transaction[] | null>(null);

  useEffect(() => {
    api.get<Transaction[]>("/payouts/me/transactions").then(setRows);
  }, []);

  if (!rows) return <Spinner />;

  return (
    <div>
      <PageHeader title="Transactions" description="Every payment, refund, and payout — chronologically, with a running balance." />
      {rows.length === 0 ? (
        <EmptyState message="No transactions yet." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3 text-right">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((t, i) => (
                <tr key={i}>
                  <td className="px-4 py-3 text-slate-500">{new Date(t.date).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${TYPE_STYLES[t.type]}`}>{t.type}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{t.description}</td>
                  <td className={`px-4 py-3 text-right font-medium ${t.amount < 0 ? "text-red-600" : "text-emerald-700"}`}>
                    {t.amount < 0 ? "-" : "+"}₹{Math.abs(t.amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-slate-800">₹{t.running_balance.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
