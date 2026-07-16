"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, StatCard, Spinner, StatusBadge } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Booking } from "@/lib/types";

export default function CustomerOverview() {
  const { user } = useAuth();
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  useEffect(() => {
    api.get<Booking[]>("/bookings").then(setBookings).catch(() => setBookings([]));
  }, []);

  if (!bookings) return <Spinner />;

  const active = bookings.filter((b) => !["completed", "cancelled", "rejected"].includes(b.status));
  const totalSpent = bookings.reduce((sum, b) => sum + b.amount_paid, 0);

  return (
    <div>
      <PageHeader title={`Welcome back, ${user?.full_name?.split(" ")[0]}`} description="Here's what's happening with your bookings." />
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Active bookings" value={active.length} />
        <StatCard label="Total bookings" value={bookings.length} />
        <StatCard label="Total spent" value={`₹${totalSpent.toLocaleString()}`} />
      </div>
      <div className="card">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Recent bookings</h2>
          <Link href="/dashboard/bookings" className="text-sm font-medium text-brand-700 hover:underline">
            View all
          </Link>
        </div>
        {bookings.length === 0 ? (
          <p className="text-sm text-slate-500">
            No bookings yet.{" "}
            <Link href="/browse" className="text-brand-700 hover:underline">
              Browse services
            </Link>{" "}
            to get started.
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {bookings.slice(0, 5).map((b) => (
              <div key={b.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-medium text-slate-800">₹{b.amount_total.toLocaleString()}</p>
                  <p className="text-slate-400">{new Date(b.created_at).toLocaleDateString()}</p>
                </div>
                <StatusBadge status={b.status} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
