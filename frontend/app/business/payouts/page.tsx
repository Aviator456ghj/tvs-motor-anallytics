"use client";

import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner, EmptyState } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { Payout, PayoutBalance } from "@/lib/types";

export default function PayoutsPage() {
  const [balance, setBalance] = useState<PayoutBalance | null>(null);
  const [payouts, setPayouts] = useState<Payout[] | null>(null);
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.get<PayoutBalance>("/payouts/me/balance").then(setBalance);
    api.get<Payout[]>("/payouts/me").then(setPayouts);
  }
  useEffect(refresh, []);

  async function requestPayout(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/payouts/me/request", { amount: Number(amount) });
      setAmount("");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not request payout");
    } finally {
      setBusy(false);
    }
  }

  if (!balance || !payouts) return <Spinner />;

  return (
    <div>
      <PageHeader title="Payouts" description="Your available balance and payout history." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Available balance" value={`₹${balance.available_balance.toLocaleString()}`} />
        <StatCard label="Lifetime gross" value={`₹${balance.lifetime_gross.toLocaleString()}`} />
        <StatCard label="Lifetime commission" value={`₹${balance.lifetime_commission.toLocaleString()}`} />
        <StatCard label="Lifetime paid out" value={`₹${balance.lifetime_paid_out.toLocaleString()}`} />
      </div>

      <form onSubmit={requestPayout} className="card my-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="label">Request payout</label>
          <input className="input w-40" type="number" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <button className="btn-primary" disabled={busy || !amount}>
          {busy ? "Processing…" : "Request payout"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>
      <p className="mb-6 text-xs text-slate-400">
        Payouts are simulated as instant for this demo — see docs/ROADMAP.md for wiring a real bank-transfer rail.
      </p>

      {payouts.length === 0 ? (
        <EmptyState message="No payouts yet." />
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
