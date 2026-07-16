"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PageHeader, Spinner, StatusBadge } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { Booking } from "@/lib/types";

interface Payment {
  id: string;
  amount: number;
  payment_type: string;
  method: string;
  status: string;
  created_at: string;
}

const CANCELLABLE = ["requested", "accepted", "scheduled"];

export default function BookingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.get<Booking>(`/bookings/${id}`).then(setBooking);
    api.get<Payment[]>(`/payments/booking/${id}`).then(setPayments);
  }

  useEffect(refresh, [id]);

  if (!booking) return <Spinner />;

  const remaining = booking.amount_total - booking.amount_paid;

  async function payRemaining() {
    setBusy(true);
    setMessage(null);
    try {
      await api.post("/payments", { booking_id: booking!.id, payment_type: "remaining", method: "upi", amount: remaining });
      refresh();
      setMessage("Payment successful.");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Payment failed");
    } finally {
      setBusy(false);
    }
  }

  async function cancelBooking() {
    setBusy(true);
    setMessage(null);
    try {
      await api.patch(`/bookings/${booking!.id}/status`, { status: "cancelled", cancellation_reason: "Customer requested cancellation" });
      refresh();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not cancel");
    } finally {
      setBusy(false);
    }
  }

  async function submitReview(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await api.post("/reviews", { booking_id: booking!.id, rating, comment });
      setMessage("Thanks for your review!");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not submit review");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="Booking details" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">Booking #{booking.id.slice(0, 8)}</p>
            <StatusBadge status={booking.status} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-slate-400">Total</p>
              <p className="font-semibold text-slate-800">₹{booking.amount_total.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-slate-400">Paid</p>
              <p className="font-semibold text-slate-800">₹{booking.amount_paid.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-slate-400">Remaining</p>
              <p className="font-semibold text-slate-800">₹{Math.max(remaining, 0).toLocaleString()}</p>
            </div>
            {booking.scheduled_date && (
              <div>
                <p className="text-slate-400">Scheduled</p>
                <p className="font-semibold text-slate-800">{booking.scheduled_date}</p>
              </div>
            )}
            {booking.service_address && (
              <div className="col-span-2">
                <p className="text-slate-400">Address</p>
                <p className="font-semibold text-slate-800">{booking.service_address}</p>
              </div>
            )}
          </div>

          {message && <p className="mt-4 text-sm text-brand-700">{message}</p>}

          <div className="mt-6 flex flex-wrap gap-3">
            {remaining > 0 && booking.status !== "cancelled" && booking.status !== "rejected" && (
              <button className="btn-primary" onClick={payRemaining} disabled={busy}>
                Pay remaining ₹{remaining.toLocaleString()}
              </button>
            )}
            {CANCELLABLE.includes(booking.status) && (
              <button className="btn-secondary" onClick={cancelBooking} disabled={busy}>
                Cancel booking
              </button>
            )}
          </div>

          {booking.status === "completed" && (
            <form onSubmit={submitReview} className="mt-8 border-t border-slate-100 pt-6">
              <h3 className="mb-3 font-semibold text-slate-900">Leave a review</h3>
              <div className="mb-3 flex gap-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button type="button" key={n} onClick={() => setRating(n)} className={n <= rating ? "text-amber-500" : "text-slate-300"}>
                    ★
                  </button>
                ))}
              </div>
              <textarea className="input mb-3" rows={3} placeholder="Share your experience…" value={comment} onChange={(e) => setComment(e.target.value)} />
              <button className="btn-primary" disabled={busy}>
                Submit review
              </button>
            </form>
          )}
        </div>

        <div className="card">
          <h3 className="mb-3 font-semibold text-slate-900">Payment history</h3>
          {payments.length === 0 ? (
            <p className="text-sm text-slate-500">No payments yet.</p>
          ) : (
            <div className="space-y-3 text-sm">
              {payments.map((p) => (
                <div key={p.id} className="flex justify-between border-b border-slate-100 pb-2 last:border-0">
                  <div>
                    <p className="font-medium capitalize text-slate-800">{p.payment_type}</p>
                    <p className="text-xs text-slate-400">{p.method.toUpperCase()} · {new Date(p.created_at).toLocaleDateString()}</p>
                  </div>
                  <p className="font-medium text-slate-800">₹{p.amount.toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
