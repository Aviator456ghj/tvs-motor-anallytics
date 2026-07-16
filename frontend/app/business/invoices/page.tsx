"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Booking } from "@/lib/types";

export default function InvoicesPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  useEffect(() => {
    api.get<Booking[]>("/bookings?status_filter=completed").then(setBookings);
  }, []);

  if (!bookings) return <Spinner />;

  return (
    <div>
      <PageHeader title="Invoices" description="Auto-generated invoice summary for each completed booking." />
      {bookings.length === 0 ? (
        <EmptyState message="Invoices are generated once bookings are marked completed." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Gross amount</th>
                <th className="px-4 py-3">Commission</th>
                <th className="px-4 py-3">Net payable</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {bookings.map((b) => (
                <tr key={b.id}>
                  <td className="px-4 py-3 text-slate-600">INV-{b.id.slice(0, 8).toUpperCase()}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">₹{b.amount_total.toLocaleString()}</td>
                  <td className="px-4 py-3 text-slate-500">−₹{b.commission_amount.toLocaleString()}</td>
                  <td className="px-4 py-3 font-semibold text-emerald-700">
                    ₹{(b.amount_total - b.commission_amount).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
