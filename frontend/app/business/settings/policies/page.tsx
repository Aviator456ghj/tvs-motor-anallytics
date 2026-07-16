"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";
import { Business } from "@/lib/types";

export default function PoliciesPage() {
  const toast = useToast();
  const [business, setBusiness] = useState<Business | null>(null);
  const [cancellation, setCancellation] = useState("");
  const [refund, setRefund] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Business & { cancellation_policy: string | null; refund_policy: string | null }>("/businesses/me").then((b) => {
      setBusiness(b);
      setCancellation(b.cancellation_policy || "");
      setRefund(b.refund_policy || "");
    });
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.patch("/businesses/me", { cancellation_policy: cancellation, refund_policy: refund });
      toast("Policies updated", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not save policies", "error");
    } finally {
      setBusy(false);
    }
  }

  if (!business) return <Spinner />;

  return (
    <div className="max-w-xl">
      <PageHeader title="Policies" description="Shown to customers before they book — sets expectations up front." />
      <form onSubmit={save} className="card space-y-4">
        <div>
          <label className="label">Cancellation policy</label>
          <textarea className="input" rows={4} placeholder="e.g. Free cancellation up to 48 hours before the booking." value={cancellation} onChange={(e) => setCancellation(e.target.value)} />
        </div>
        <div>
          <label className="label">Refund policy</label>
          <textarea className="input" rows={4} placeholder="e.g. Refunds are processed within 5-7 business days." value={refund} onChange={(e) => setRefund(e.target.value)} />
        </div>
        <button className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Save policies"}</button>
      </form>
    </div>
  );
}
