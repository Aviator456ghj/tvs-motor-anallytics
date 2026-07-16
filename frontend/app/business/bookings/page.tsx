"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { BookingEvent, BookingListItem, BookingStatus } from "@/lib/types";

const NEXT_STATUS: Partial<Record<BookingStatus, BookingStatus[]>> = {
  requested: ["accepted", "rejected"],
  accepted: ["scheduled"],
  scheduled: ["in_progress"],
  in_progress: ["completed"],
};

const STATUS_TABS: { id: BookingStatus | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "requested", label: "Requested" },
  { id: "accepted", label: "Accepted" },
  { id: "scheduled", label: "Scheduled" },
  { id: "in_progress", label: "In progress" },
  { id: "completed", label: "Completed" },
  { id: "cancelled", label: "Cancelled" },
];

export default function OrdersPage() {
  const [bookings, setBookings] = useState<BookingListItem[] | null>(null);
  const [statusTab, setStatusTab] = useState<BookingStatus | "all">("all");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    const qs = new URLSearchParams();
    if (statusTab !== "all") qs.set("status_filter", statusTab);
    if (q) qs.set("q", q);
    api.get<BookingListItem[]>(`/bookings?${qs.toString()}`).then(setBookings);
  }

  useEffect(refresh, [statusTab, q]);

  async function transition(id: string, status: BookingStatus) {
    setError(null);
    try {
      await api.patch(`/bookings/${id}/status`, { status });
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update booking");
    }
  }

  async function bulkAccept() {
    for (const id of selected) {
      const b = bookings?.find((x) => x.id === id);
      if (b?.status === "requested") await transition(id, "accepted");
    }
    setSelected(new Set());
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const active = bookings?.find((b) => b.id === activeId) || null;

  if (!bookings) return <Spinner />;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <PageHeader title="Orders" description="Every booking, searchable and filterable — accept, schedule, tag, refund." />
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
      <div className="mb-4 flex gap-2">
        <input className="input max-w-xs" placeholder="Search by customer name…" value={q} onChange={(e) => setQ(e.target.value)} />
        {selected.size > 0 && (
          <button className="btn-secondary text-sm" onClick={bulkAccept}>
            Accept {selected.size} selected
          </button>
        )}
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {bookings.length === 0 ? (
        <EmptyState message="No orders match these filters." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="w-8 px-4 py-3"></th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Tags</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {bookings.map((b) => (
                <tr key={b.id} className="cursor-pointer hover:bg-slate-50" onClick={() => setActiveId(b.id)}>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" checked={selected.has(b.id)} onChange={() => toggleSelect(b.id)} />
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-800">{b.customer_name}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {b.service_title} · {b.package_name}
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-800">₹{b.amount_total.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={b.status} />
                  </td>
                  <td className="px-4 py-3">
                    {(b.tags || "")
                      .split(",")
                      .filter(Boolean)
                      .map((t) => (
                        <span key={t} className="badge mr-1 bg-slate-100 text-slate-500">
                          {t}
                        </span>
                      ))}
                  </td>
                  <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex justify-end gap-2">
                      {(NEXT_STATUS[b.status] || []).map((next) => (
                        <button key={next} onClick={() => transition(b.id, next)} className="btn-secondary text-xs capitalize">
                          {next.replace("_", " ")}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {active && <OrderDrawer booking={active} onClose={() => setActiveId(null)} onChanged={refresh} />}
    </div>
  );
}

function OrderDrawer({ booking, onClose, onChanged }: { booking: BookingListItem; onClose: () => void; onChanged: () => void }) {
  const [events, setEvents] = useState<BookingEvent[] | null>(null);
  const [note, setNote] = useState("");
  const [tagsInput, setTagsInput] = useState(booking.tags || "");
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  function refreshEvents() {
    api.get<BookingEvent[]>(`/bookings/${booking.id}/events`).then(setEvents);
  }
  useEffect(refreshEvents, [booking.id]);

  const refundable = useMemo(() => booking.amount_paid - booking.amount_refunded, [booking]);

  async function saveTags() {
    setBusy(true);
    try {
      await api.patch(`/bookings/${booking.id}/tags`, { tags: tagsInput.split(",").map((t) => t.trim()) });
      onChanged();
      refreshEvents();
      setMsg("Tags updated.");
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "Could not update tags");
    } finally {
      setBusy(false);
    }
  }

  async function addNote() {
    if (!note.trim()) return;
    setBusy(true);
    try {
      await api.post(`/bookings/${booking.id}/notes?message=${encodeURIComponent(note)}`);
      setNote("");
      refreshEvents();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "Could not add note");
    } finally {
      setBusy(false);
    }
  }

  async function issueRefund() {
    setBusy(true);
    setMsg(null);
    try {
      await api.post(`/bookings/${booking.id}/refund`, { amount: Number(refundAmount), reason: refundReason });
      setRefundAmount("");
      setRefundReason("");
      onChanged();
      refreshEvents();
      setMsg("Refund issued to customer's wallet.");
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "Could not issue refund");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/30" onClick={onClose}>
      <div className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400">Order #{booking.id.slice(0, 8)}</p>
            <p className="font-semibold text-slate-900">{booking.customer_name}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            ✕
          </button>
        </div>

        <div className="mb-4 grid grid-cols-3 gap-3 text-sm">
          <div>
            <p className="text-slate-400">Total</p>
            <p className="font-semibold">₹{booking.amount_total.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-slate-400">Paid</p>
            <p className="font-semibold">₹{booking.amount_paid.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-slate-400">Refunded</p>
            <p className="font-semibold">₹{booking.amount_refunded.toLocaleString()}</p>
          </div>
        </div>

        {msg && <p className="mb-3 text-sm text-brand-700">{msg}</p>}

        <div className="mb-5">
          <label className="label">Tags (comma separated)</label>
          <div className="flex gap-2">
            <input className="input" value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} placeholder="vip, urgent" />
            <button className="btn-secondary text-xs" onClick={saveTags} disabled={busy}>
              Save
            </button>
          </div>
        </div>

        {refundable > 0 && (
          <div className="mb-5 rounded-lg border border-slate-200 p-3">
            <p className="mb-2 text-sm font-semibold text-slate-800">Issue a refund</p>
            <p className="mb-2 text-xs text-slate-500">Refundable: ₹{refundable.toLocaleString()}</p>
            <div className="flex flex-col gap-2">
              <input className="input" type="number" placeholder="Amount" value={refundAmount} onChange={(e) => setRefundAmount(e.target.value)} />
              <input className="input" placeholder="Reason" value={refundReason} onChange={(e) => setRefundReason(e.target.value)} />
              <button className="btn-secondary text-xs" onClick={issueRefund} disabled={busy || !refundAmount || !refundReason}>
                Issue refund
              </button>
            </div>
          </div>
        )}

        <div>
          <p className="mb-2 text-sm font-semibold text-slate-800">Timeline</p>
          <div className="mb-3 flex gap-2">
            <input className="input" placeholder="Add an internal note…" value={note} onChange={(e) => setNote(e.target.value)} />
            <button className="btn-secondary text-xs" onClick={addNote} disabled={busy}>
              Add
            </button>
          </div>
          {!events ? (
            <Spinner />
          ) : (
            <div className="space-y-3">
              {[...events].reverse().map((e) => (
                <div key={e.id} className="border-l-2 border-slate-200 pl-3 text-xs">
                  <p className="text-slate-700">{e.message}</p>
                  <p className="text-slate-400">{new Date(e.created_at).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
