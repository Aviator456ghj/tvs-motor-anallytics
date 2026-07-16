"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { Booking } from "@/lib/types";

export default function CalendarPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  useEffect(() => {
    api.get<Booking[]>("/bookings").then(setBookings);
  }, []);

  if (!bookings) return <Spinner />;

  const upcoming = bookings
    .filter((b) => b.scheduled_date && !["cancelled", "rejected", "completed"].includes(b.status))
    .sort((a, b) => (a.scheduled_date! < b.scheduled_date! ? -1 : 1));

  const byDate = upcoming.reduce<Record<string, Booking[]>>((acc, b) => {
    const key = b.scheduled_date!;
    acc[key] = acc[key] || [];
    acc[key].push(b);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader title="Calendar" description="Your upcoming scheduled bookings, grouped by date." />
      {Object.keys(byDate).length === 0 ? (
        <EmptyState message="No scheduled bookings yet. Accepted bookings will show up here once a date is confirmed." />
      ) : (
        <div className="space-y-4">
          {Object.entries(byDate).map(([date, items]) => (
            <div key={date} className="card">
              <h3 className="mb-3 font-semibold text-slate-900">{new Date(date).toDateString()}</h3>
              <div className="space-y-2">
                {items.map((b) => (
                  <div key={b.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <span className="text-slate-600">₹{b.amount_total.toLocaleString()} · {b.scheduled_time?.slice(0, 5) || "Time TBD"}</span>
                    <StatusBadge status={b.status} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
