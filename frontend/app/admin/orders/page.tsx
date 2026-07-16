"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { BookingListItem, BookingStatus } from "@/lib/types";

const STATUS_TABS: { id: BookingStatus | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "requested", label: "Requested" },
  { id: "accepted", label: "Accepted" },
  { id: "scheduled", label: "Scheduled" },
  { id: "in_progress", label: "In progress" },
  { id: "completed", label: "Completed" },
  { id: "cancelled", label: "Cancelled" },
];

export default function AdminOrdersPage() {
  const [bookings, setBookings] = useState<BookingListItem[] | null>(null);
  const [statusTab, setStatusTab] = useState<BookingStatus | "all">("all");
  const [q, setQ] = useState("");

  useEffect(() => {
    const qs = new URLSearchParams();
    if (statusTab !== "all") qs.set("status_filter", statusTab);
    if (q) qs.set("q", q);
    api.get<BookingListItem[]>(`/bookings?${qs.toString()}`).then(setBookings);
  }, [statusTab, q]);

  if (!bookings) return <Spinner />;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <PageHeader title="All orders" description="Every booking across every business on the platform." />
        <a href={`${process.env.NEXT_PUBLIC_API_URL}/bookings/export`} target="_blank" rel="noreferrer" className="btn-secondary text-sm">
          Export CSV
        </a>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {STATUS_TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setStatusTab(t.id)}
            className={`badge ${statusTab === t.id ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-500"}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <input className="input mb-4 max-w-xs" placeholder="Search by customer or business…" value={q} onChange={(e) => setQ(e.target.value)} />

      {bookings.length === 0 ? (
        <EmptyState message="No orders match these filters." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Business</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Commission</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {bookings.map((b) => (
                <tr key={b.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{b.customer_name}</td>
                  <td className="px-4 py-3 text-slate-600">{b.business_name}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">₹{b.amount_total.toLocaleString()}</td>
                  <td className="px-4 py-3 text-slate-500">₹{b.commission_amount.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={b.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500">{new Date(b.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
