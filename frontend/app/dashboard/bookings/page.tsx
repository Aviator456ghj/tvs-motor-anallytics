"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, StatusBadge, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Booking } from "@/lib/types";

export default function BookingHistoryPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  useEffect(() => {
    api.get<Booking[]>("/bookings").then(setBookings).catch(() => setBookings([]));
  }, []);

  if (!bookings) return <Spinner />;

  return (
    <div>
      <PageHeader title="Booking history" description="All your service requests, past and present." />
      {bookings.length === 0 ? (
        <EmptyState message="You haven't made any bookings yet." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Paid</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {bookings.map((b) => (
                <tr key={b.id}>
                  <td className="px-4 py-3 text-slate-500">{new Date(b.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">₹{b.amount_total.toLocaleString()}</td>
                  <td className="px-4 py-3 text-slate-500">₹{b.amount_paid.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={b.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/dashboard/bookings/${b.id}`} className="text-brand-700 hover:underline">
                      View
                    </Link>
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
