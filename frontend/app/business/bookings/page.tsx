"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { Booking, BookingStatus } from "@/lib/types";

const NEXT_STATUS: Partial<Record<BookingStatus, BookingStatus[]>> = {
  requested: ["accepted", "rejected"],
  accepted: ["scheduled"],
  scheduled: ["in_progress"],
  in_progress: ["completed"],
};

export default function BookingRequestsPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.get<Booking[]>("/bookings").then(setBookings);
  }

  useEffect(refresh, []);

  async function transition(id: string, status: BookingStatus) {
    setError(null);
    try {
      await api.patch(`/bookings/${id}/status`, { status });
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update booking");
    }
  }

  if (!bookings) return <Spinner />;

  return (
    <div>
      <PageHeader title="Booking requests" description="Accept, schedule, and fulfil customer bookings." />
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {bookings.length === 0 ? (
        <EmptyState message="No bookings yet." />
      ) : (
        <div className="space-y-3">
          {bookings.map((b) => (
            <div key={b.id} className="card flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium text-slate-800">₹{b.amount_total.toLocaleString()} · Booking #{b.id.slice(0, 8)}</p>
                <p className="text-xs text-slate-400">
                  {new Date(b.created_at).toLocaleDateString()} {b.scheduled_date && `· Scheduled ${b.scheduled_date}`}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={b.status} />
                <div className="flex gap-2">
                  {(NEXT_STATUS[b.status] || []).map((next) => (
                    <button key={next} onClick={() => transition(b.id, next)} className="btn-secondary text-xs capitalize">
                      {next.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
