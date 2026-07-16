"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";
import { BookingEvent, BookingListItem, BookingStatus, Service } from "@/lib/types";

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
  return (
    <Suspense>
      <OrdersContent />
    </Suspense>
  );
}

function OrdersContent() {
  const toast = useToast();
  const router = useRouter();
  const params = useSearchParams();
  const [bookings, setBookings] = useState<BookingListItem[] | null>(null);
  const [statusTab, setStatusTab] = useState<BookingStatus | "all">("all");
  const [q, setQ] = useState(params.get("q") || "");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(params.get("create") === "1");

  useEffect(() => {
    if (params.get("create") === "1") setShowCreate(true);
  }, [params]);

  function refresh() {
    const qs = new URLSearchParams();
    if (statusTab !== "all") qs.set("status_filter", statusTab);
    if (q) qs.set("q", q);
    api.get<BookingListItem[]>(`/bookings?${qs.toString()}`).then(setBookings);
  }

  useEffect(refresh, [statusTab, q]);

  async function transition(id: string, status: BookingStatus) {
    try {
      await api.patch(`/bookings/${id}/status`, { status });
      refresh();
      toast(`Order marked as ${status.replace("_", " ")}`, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not update booking", "error");
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
        <div className="flex gap-2">
          <a href={`${process.env.NEXT_PUBLIC_API_URL}/bookings/export`} target="_blank" rel="noreferrer" className="btn-secondary text-sm">
            Export CSV
          </a>
          <button className="btn-primary text-sm" onClick={() => setShowCreate(true)}>
            Create order
          </button>
        </div>
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
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {b.customer_name}
                    {b.created_via === "manual" && <span className="badge ml-1.5 bg-slate-100 text-slate-500">Manual</span>}
                  </td>
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
      {showCreate && (
        <CreateOrderModal
          onClose={() => {
            setShowCreate(false);
            router.replace("/business/bookings");
          }}
          onCreated={() => {
            refresh();
            setShowCreate(false);
            router.replace("/business/bookings");
          }}
        />
      )}
    </div>
  );
}

function CreateOrderModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const toast = useToast();
  const [services, setServices] = useState<Service[] | null>(null);
  const [form, setForm] = useState({ customer_email: "", service_id: "", package_id: "", scheduled_date: "", service_address: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Service[]>("/services/me").then((list) => {
      setServices(list);
      if (list[0]) setForm((f) => ({ ...f, service_id: list[0].id, package_id: list[0].packages[0]?.id || "" }));
    });
  }, []);

  const activeService = services?.find((s) => s.id === form.service_id);
  const activePackage = activeService?.packages.find((p) => p.id === form.package_id);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/bookings/manual", {
        customer_email: form.customer_email,
        service_id: form.service_id,
        package_id: form.package_id,
        scheduled_date: form.scheduled_date || undefined,
        service_address: form.service_address || undefined,
        notes: form.notes || undefined,
      });
      toast("Order created", "success");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create order");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/30 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Create order</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">✕</button>
        </div>
        <p className="mb-4 text-xs text-slate-500">For phone or walk-in bookings. The customer must already have a ServicesOS account.</p>
        {!services ? (
          <Spinner />
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="label">Customer email</label>
              <input className="input" type="email" required value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })} />
            </div>
            <div>
              <label className="label">Service</label>
              <select
                className="input"
                value={form.service_id}
                onChange={(e) => {
                  const svc = services.find((s) => s.id === e.target.value);
                  setForm({ ...form, service_id: e.target.value, package_id: svc?.packages[0]?.id || "" });
                }}
              >
                {services.map((s) => (
                  <option key={s.id} value={s.id}>{s.title}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Package</label>
              <select className="input" value={form.package_id} onChange={(e) => setForm({ ...form, package_id: e.target.value })}>
                {activeService?.packages.map((p) => (
                  <option key={p.id} value={p.id}>{p.name} — ₹{p.price.toLocaleString()}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Date</label>
              <input className="input" type="date" value={form.scheduled_date} onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })} />
            </div>
            <div>
              <label className="label">Service address (optional)</label>
              <input className="input" value={form.service_address} onChange={(e) => setForm({ ...form, service_address: e.target.value })} />
            </div>
            {activePackage && (
              <div className="summary-box rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600">
                Total: <b>₹{activePackage.price.toLocaleString()}</b> — booking will be created as <b>Accepted</b>.
              </div>
            )}
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button className="btn-primary w-full" disabled={busy || !form.package_id}>
              {busy ? "Creating…" : "Create order"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function OrderDrawer({ booking, onClose, onChanged }: { booking: BookingListItem; onClose: () => void; onChanged: () => void }) {
  const toast = useToast();
  const [events, setEvents] = useState<BookingEvent[] | null>(null);
  const [note, setNote] = useState("");
  const [tagsInput, setTagsInput] = useState(booking.tags || "");
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [busy, setBusy] = useState(false);

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
      toast("Tags updated", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not update tags", "error");
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
      toast("Note added", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not add note", "error");
    } finally {
      setBusy(false);
    }
  }

  async function issueRefund() {
    setBusy(true);
    try {
      await api.post(`/bookings/${booking.id}/refund`, { amount: Number(refundAmount), reason: refundReason });
      setRefundAmount("");
      setRefundReason("");
      onChanged();
      refreshEvents();
      toast("Refund issued to customer's wallet", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not issue refund", "error");
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
