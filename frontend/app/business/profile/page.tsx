"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { Business } from "@/lib/types";

export default function CompanyProfilePage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [form, setForm] = useState<Partial<Business>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get<Business>("/businesses/me").then((b) => {
      setBusiness(b);
      setForm(b);
    });
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.patch<Business>("/businesses/me", {
        company_name: form.company_name,
        tagline: form.tagline,
        description: form.description,
        city: form.city,
        state: form.state,
        experience_years: form.experience_years,
        offers_home_service: form.offers_home_service,
        offers_instant_booking: form.offers_instant_booking,
      });
      setBusiness(updated);
      setMessage("Profile updated.");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

  if (!business) return <Spinner />;

  return (
    <div className="max-w-2xl">
      <PageHeader title="Company profile" description="This is what customers see on your public profile." />
      <form onSubmit={save} className="card space-y-4">
        <div>
          <label className="label">Company name</label>
          <input className="input" value={form.company_name || ""} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
        </div>
        <div>
          <label className="label">Tagline</label>
          <input className="input" value={form.tagline || ""} onChange={(e) => setForm({ ...form, tagline: e.target.value })} />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea className="input" rows={4} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">City</label>
            <input className="input" value={form.city || ""} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </div>
          <div>
            <label className="label">State</label>
            <input className="input" value={form.state || ""} onChange={(e) => setForm({ ...form, state: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label">Years of experience</label>
          <input
            className="input"
            type="number"
            value={form.experience_years ?? 0}
            onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })}
          />
        </div>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={!!form.offers_home_service}
              onChange={(e) => setForm({ ...form, offers_home_service: e.target.checked })}
            />
            Home service
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={!!form.offers_instant_booking}
              onChange={(e) => setForm({ ...form, offers_instant_booking: e.target.checked })}
            />
            Instant booking
          </label>
        </div>
        {message && <p className="text-sm text-brand-700">{message}</p>}
        <button className="btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </button>
      </form>
    </div>
  );
}
