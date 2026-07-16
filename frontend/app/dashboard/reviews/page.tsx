"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { Booking } from "@/lib/types";

export default function CustomerReviewsPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  useEffect(() => {
    api.get<Booking[]>("/bookings?status_filter=completed").then(setBookings).catch(() => setBookings([]));
  }, []);

  if (!bookings) return <Spinner />;

  return (
    <div>
      <PageHeader title="Reviews" description="Completed bookings you can review or have already reviewed." />
      {bookings.length === 0 ? (
        <EmptyState message="No completed bookings yet — reviews unlock once a service is delivered." />
      ) : (
        <div className="space-y-3">
          {bookings.map((b) => (
            <Link key={b.id} href={`/dashboard/bookings/${b.id}`} className="card flex items-center justify-between hover:shadow-md">
              <div>
                <p className="font-medium text-slate-800">Booking #{b.id.slice(0, 8)}</p>
                <p className="text-xs text-slate-400">Completed {new Date(b.created_at).toLocaleDateString()}</p>
              </div>
              <StatusBadge status={b.status} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
