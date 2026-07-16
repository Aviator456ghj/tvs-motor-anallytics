"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";
import { Business } from "@/lib/types";

type Prefs = { notify_email_bookings: boolean; notify_email_payments: boolean; notify_email_marketing: boolean };

const OPTIONS: { key: keyof Prefs; label: string; desc: string }[] = [
  { key: "notify_email_bookings", label: "New bookings & status changes", desc: "Booking requests, acceptances, cancellations." },
  { key: "notify_email_payments", label: "Payments & payouts", desc: "Payment received, refunds issued, payout sent." },
  { key: "notify_email_marketing", label: "Product updates & tips", desc: "Occasional emails about new ServicesOS features." },
];

export default function NotificationsSettingsPage() {
  const toast = useToast();
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Business & Prefs>("/businesses/me").then((b) =>
      setPrefs({ notify_email_bookings: b.notify_email_bookings, notify_email_payments: b.notify_email_payments, notify_email_marketing: b.notify_email_marketing })
    );
  }, []);

  async function toggle(key: keyof Prefs) {
    if (!prefs) return;
    const next = { ...prefs, [key]: !prefs[key] };
    setPrefs(next);
    setBusy(true);
    try {
      await api.put("/businesses/me/notification-preferences", next);
      toast("Preferences saved", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not save", "error");
    } finally {
      setBusy(false);
    }
  }

  if (!prefs) return <Spinner />;

  return (
    <div className="max-w-lg">
      <PageHeader title="Notifications" description="What we email you about." />
      <div className="card divide-y divide-slate-100">
        {OPTIONS.map((o) => (
          <label key={o.key} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
            <div>
              <p className="text-sm font-medium text-slate-800">{o.label}</p>
              <p className="text-xs text-slate-500">{o.desc}</p>
            </div>
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={prefs[o.key]}
              disabled={busy}
              onChange={() => toggle(o.key)}
            />
          </label>
        ))}
      </div>
    </div>
  );
}
