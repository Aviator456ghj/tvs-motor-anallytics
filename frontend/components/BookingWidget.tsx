"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { Booking, Package, Service } from "@/lib/types";

export default function BookingWidget({ businessId, services }: { businessId: string; services: Service[] }) {
  const { user } = useAuth();
  const router = useRouter();

  const [serviceId, setServiceId] = useState(services[0]?.id || "");
  const [packageId, setPackageId] = useState(services[0]?.packages[0]?.id || "");
  const [date, setDate] = useState("");
  const [address, setAddress] = useState("");
  const [coupon, setCoupon] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);

  const activeService = services.find((s) => s.id === serviceId);
  const activePackage = activeService?.packages.find((p: Package) => p.id === packageId);

  async function submitBooking(e: React.FormEvent) {
    e.preventDefault();
    if (!user) {
      router.push("/login");
      return;
    }
    if (user.role !== "customer") {
      setError("Only customer accounts can book services.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const created = await api.post<Booking>("/bookings", {
        business_id: businessId,
        service_id: serviceId,
        package_id: packageId,
        scheduled_date: date || undefined,
        service_address: address || undefined,
        coupon_code: coupon || undefined,
      });
      setBooking(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create booking");
    } finally {
      setLoading(false);
    }
  }

  async function payAdvance() {
    if (!booking) return;
    setLoading(true);
    try {
      await api.post("/payments", {
        booking_id: booking.id,
        payment_type: "advance",
        method: "upi",
        amount: booking.amount_advance,
      });
      router.push("/dashboard/bookings");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Payment failed");
    } finally {
      setLoading(false);
    }
  }

  if (booking) {
    return (
      <div className="card">
        <h3 className="mb-2 font-semibold text-slate-900">Booking request sent!</h3>
        <p className="text-sm text-slate-600">
          Total: ₹{booking.amount_total.toLocaleString()} · Advance due: ₹{booking.amount_advance.toLocaleString()}
        </p>
        <p className="mt-1 text-xs text-slate-400">Status: {booking.status}. Pay the advance to secure your slot.</p>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <button className="btn-primary mt-4 w-full" onClick={payAdvance} disabled={loading}>
          {loading ? "Processing…" : `Pay advance ₹${booking.amount_advance.toLocaleString()}`}
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={submitBooking} className="card space-y-4">
      <h3 className="font-semibold text-slate-900">Book this provider</h3>
      <div>
        <label className="label">Service</label>
        <select
          className="input"
          value={serviceId}
          onChange={(e) => {
            setServiceId(e.target.value);
            const svc = services.find((s) => s.id === e.target.value);
            setPackageId(svc?.packages[0]?.id || "");
          }}
        >
          {services.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Package</label>
        <select className="input" value={packageId} onChange={(e) => setPackageId(e.target.value)}>
          {activeService?.packages.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} — ₹{p.price.toLocaleString()}
            </option>
          ))}
        </select>
        {activePackage?.description && <p className="mt-1 text-xs text-slate-400">{activePackage.description}</p>}
      </div>
      <div>
        <label className="label">Preferred date</label>
        <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>
      <div>
        <label className="label">Service address (for home service)</label>
        <input className="input" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Optional" />
      </div>
      <div>
        <label className="label">Coupon code</label>
        <input className="input" value={coupon} onChange={(e) => setCoupon(e.target.value.toUpperCase())} placeholder="e.g. WELCOME10" />
      </div>
      {activePackage && (
        <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
          Package price: <span className="font-semibold text-slate-900">₹{activePackage.price.toLocaleString()}</span>
          <br />
          Advance (30%) due now: ₹{Math.round(activePackage.price * 0.3).toLocaleString()}
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button className="btn-primary w-full" disabled={loading || !packageId}>
        {loading ? "Booking…" : "Request booking"}
      </button>
    </form>
  );
}
