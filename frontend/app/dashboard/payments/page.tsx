"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Booking } from "@/lib/types";

export default function PaymentsPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  useEffect(() => {
    api.get<Booking[]>("/bookings").then(setBookings).catch(() => setBookings([]));
  }, []);

  if (!bookings) return <Spinner />;

  const totalPaid = bookings.reduce((sum, b) => sum + b.amount_paid, 0);
  const totalDue = bookings.reduce((sum, b) => sum + Math.max(b.amount_total - b.amount_paid, 0), 0);

  return (
    <div>
      <PageHeader title="Payments" description="Advance and final payments across all your bookings." />
      <div className="mb-6 grid grid-cols-2 gap-4 sm:w-96">
        <div className="card">
          <p className="text-sm text-slate-500">Total paid</p>
          <p className="text-xl font-bold text-slate-900">₹{totalPaid.toLocaleString()}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Outstanding</p>
          <p className="text-xl font-bold text-slate-900">₹{totalDue.toLocaleString()}</p>
        </div>
      </div>
      {bookings.length === 0 ? (
        <EmptyState message="No payments yet." />
      ) : (
        <div className="space-y-3">
          {bookings.map((b) => (
            <Link key={b.id} href={`/dashboard/bookings/${b.id}`} className="card flex items-center justify-between hover:shadow-md">
              <div>
                <p className="font-medium text-slate-800">Booking #{b.id.slice(0, 8)}</p>
                <p className="text-xs text-slate-400">{new Date(b.created_at).toLocaleDateString()}</p>
              </div>
              <div className="text-right text-sm">
                <p className="text-slate-800">Paid ₹{b.amount_paid.toLocaleString()} / ₹{b.amount_total.toLocaleString()}</p>
                {b.amount_total - b.amount_paid > 0 && <p className="text-amber-600">₹{(b.amount_total - b.amount_paid).toLocaleString()} due</p>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
